import datetime

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    Certification, InstituteProfile, Qualification, TeacherProfile, UniversityProfile, User,
)

from .matching import compute_match_breakdown, compute_match_score
from .models import JobApplication, JobPost, JobQuestion


def make_teacher(email="t@x.com", **kw):
    u = User.objects.create_user(email=email, password="pw12345678", role="teacher")
    defaults = dict(first_name="Asha", subjects=["Physics"], total_experience_years=5, city="Bengaluru",
                    state="Karnataka", salary_expectation=600000)
    defaults.update(kw)
    return TeacherProfile.objects.create(user=u, **defaults)


def make_institute(email="i@x.com", name="Greenwood High"):
    u = User.objects.create_user(email=email, password="pw12345678", role="institute")
    return InstituteProfile.objects.create(user=u, name=name)


def make_university(email="uni@x.com", name="Bangalore University", verified=True, nirf=None):
    u = User.objects.create_user(email=email, password="pw12345678", role="university")
    uni = UniversityProfile.objects.create(user=u, name=name, nirf_rank=nirf)
    if verified:  # saving as verified mints the Ed25519 key pair
        uni.verification_status = "verified"
        uni.save()
    return uni


def make_degree(teacher, uni, level="bachelors", course="B.Sc.", year=2015, pdf=b"%PDF-1.4 degree", **kw):
    return Qualification.objects.create(
        teacher=teacher, university=uni, level=level, course=course, year_of_passing=year,
        marksheet=SimpleUploadedFile("m.pdf", b"%PDF-1.4 marks"),
        degree_certificate=SimpleUploadedFile("d.pdf", pdf), **kw,
    )


def make_job(inst, **kw):
    defaults = dict(title="PGT Physics", description="d", specialization="Physics", min_experience_years=3,
                    city="Bengaluru", state="Karnataka", salary_min=400000, salary_max=700000)
    defaults.update(kw)
    return JobPost.objects.create(institute=inst, **defaults)


def auth(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


class MatchingTests(TestCase):
    def setUp(self):
        self.inst = make_institute()

    def test_perfect_match_scores_100(self):
        t, j = make_teacher(), make_job(self.inst)
        self.assertEqual(compute_match_score(t, j), 100.0)

    def test_score_always_within_0_100(self):
        t = make_teacher(subjects=["Dance"], total_experience_years=0, city="Delhi", state="Delhi",
                         salary_expectation=9_000_000, salary_negotiable=False)
        j = make_job(self.inst, min_experience_years=10, salary_negotiable=False)
        s = compute_match_score(t, j)
        self.assertGreaterEqual(s, 0)
        self.assertLessEqual(s, 100)
        self.assertLess(s, 10)

    def test_subject_synonyms_and_role_words(self):
        t = make_teacher(subjects=["Maths"])
        j = make_job(self.inst, specialization="", title="PGT Mathematics Teacher (Grades 9-10)")
        self.assertEqual(compute_match_breakdown(t, j)["factors"]["subject"]["score"], 100)

    def test_subject_from_past_employment(self):
        from accounts.models import EmploymentHistory
        t = make_teacher(subjects=[])
        EmploymentHistory.objects.create(teacher=t, institute_name="X", designation="TGT",
                                         subjects=["Physics"], start_date=datetime.date(2020, 1, 1))
        self.assertEqual(compute_match_breakdown(t, make_job(self.inst))["factors"]["subject"]["score"], 100)

    def test_wrong_subject_zero(self):
        t = make_teacher(subjects=["History"])
        self.assertEqual(compute_match_breakdown(t, make_job(self.inst))["factors"]["subject"]["score"], 0)

    def test_experience_shortfall_is_proportional(self):
        t = make_teacher(total_experience_years=2)
        j = make_job(self.inst, min_experience_years=4)
        self.assertEqual(compute_match_breakdown(t, j)["factors"]["experience"]["score"], 50)

    def test_location_tiers(self):
        j = make_job(self.inst)
        n = iter(range(100))
        f = lambda **kw: compute_match_breakdown(make_teacher(email=f"loc{next(n)}@x.com", **kw), j)["factors"]["location"]["score"]
        self.assertEqual(f(city="bengaluru "), 100)                                  # case/space insensitive
        self.assertEqual(f(city="Mysuru"), 40)                                       # same state, won't move
        self.assertEqual(f(city="Mysuru", willing_to_relocate=True), 70)
        self.assertEqual(f(city="Pune", state="Maharashtra", willing_to_relocate=True), 60)
        self.assertEqual(f(city="Pune", state="Maharashtra", preferred_cities=["Bengaluru"]), 90)
        self.assertEqual(f(city="Pune", state="Maharashtra"), 0)

    def test_remote_ignores_location(self):
        t = make_teacher(city="Pune", state="Maharashtra")
        j = make_job(self.inst, work_mode="remote")
        self.assertEqual(compute_match_breakdown(t, j)["factors"]["location"]["score"], 100)

    def test_salary_tiers(self):
        j = make_job(self.inst, salary_negotiable=True)
        sal = lambda x, neg=True: compute_match_breakdown(
            make_teacher(email=f"s{x}{neg}@x.com", salary_expectation=x, salary_negotiable=neg), j)["factors"]["salary"]["score"]
        self.assertEqual(sal(500000), 100)
        self.assertEqual(sal(760000), 85)       # within +10% negotiable tolerance
        self.assertLess(sal(900000), 85)
        self.assertEqual(sal(5_000_000), 0)

    def test_missing_data_is_neutral_not_punishing(self):
        t = make_teacher(salary_expectation=None, subjects=[], city="", state="")
        j = make_job(self.inst)
        fs = compute_match_breakdown(t, j)["factors"]
        self.assertEqual(fs["salary"]["score"], 50)
        self.assertEqual(fs["subject"]["score"], 50)
        self.assertEqual(fs["location"]["score"], 50)


class ApplyFlowTests(TestCase):
    def setUp(self):
        self.inst = make_institute()
        self.job = make_job(self.inst)
        self.teacher = make_teacher()
        self.client_t = auth(self.teacher.user)

    def test_apply_sets_score_and_breakdown(self):
        r = self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["match_score"], 100.0)
        self.assertIsNone(r.data["match_breakdown"])  # teachers don't see the breakdown
        app = JobApplication.objects.get()
        self.assertEqual(set(app.match_breakdown["factors"]), {"subject", "experience", "location", "salary"})

    def test_apply_auto_attaches_only_uploaded_documents(self):
        f = lambda n: SimpleUploadedFile(n, b"%PDF-1.4 test")
        uni = make_university()
        q_deg = make_degree(self.teacher, uni, level="masters", course="M.Sc.")
        q_marks = make_degree(self.teacher, uni, level="bachelors", course="B.Ed.", year=2013)
        c_doc = Certification.objects.create(teacher=self.teacher, name="CTET", document=f("c.pdf"))
        Certification.objects.create(teacher=self.teacher, name="NET")  # no file

        r = self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        app = JobApplication.objects.get()
        self.assertEqual({q.id for q in app.attached_qualifications.all()}, {q_deg.id, q_marks.id})
        self.assertEqual([c.id for c in app.attached_certifications.all()], [c_doc.id])
        self.assertEqual(len(r.data["attached_qualifications"]), 2)
        self.assertEqual(len(r.data["attached_certifications"]), 1)

    def test_other_teachers_documents_never_attached(self):
        other = make_teacher(email="o@x.com")
        Certification.objects.create(teacher=other, name="NET", document=SimpleUploadedFile("n.pdf", b"x"))
        self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.assertEqual(JobApplication.objects.get().attached_certifications.count(), 0)

    def test_duplicate_application_rejected(self):
        self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        r = self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(JobApplication.objects.count(), 1)

    def test_scoring_failure_does_not_block_application(self):
        from unittest import mock
        with mock.patch("jobs.views.compute_match_breakdown", side_effect=RuntimeError("boom")):
            r = self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data["match_score"])

    def test_institute_sees_breakdown_and_can_sort_by_score(self):
        weak = make_teacher(email="w@x.com", subjects=["History"], first_name="Weak")
        auth(weak.user).post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        self.client_t.post(f"/api/jobs/{self.job.id}/apply/", {}, format="json")
        ci = auth(self.inst.user)
        r = ci.get("/api/applications/", {"job": self.job.id, "ordering": "-match_score"})
        scores = [a["match_score"] for a in r.data]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertIsNotNone(r.data[0]["match_breakdown"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SITE_URL="https://aeterna.test")
class NotificationTests(TestCase):
    def setUp(self):
        self.inst = make_institute()
        self.job = make_job(self.inst)
        self.teacher = make_teacher()
        self.app = JobApplication.objects.create(job=self.job, teacher=self.teacher)
        self.ci = auth(self.inst.user)

    def patch(self, status):
        with self.captureOnCommitCallbacks(execute=True):
            return self.ci.patch(f"/api/applications/{self.app.id}/", {"status": status}, format="json")

    def test_shortlisted_sends_email_to_teacher(self):
        self.assertEqual(self.patch("shortlisted").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["t@x.com"])
        self.assertIn("shortlisted", m.subject.lower())
        self.assertIn("Greenwood High", m.body)
        self.assertIn("https://aeterna.test/applications", m.body)

    def test_internal_statuses_send_nothing(self):
        self.patch("viewed")
        self.patch("bookmarked")
        self.assertEqual(len(mail.outbox), 0)

    def test_same_status_twice_sends_once(self):
        self.patch("hired")
        self.patch("hired")
        self.assertEqual(len(mail.outbox), 1)

    def test_mail_failure_does_not_break_update(self):
        from unittest import mock
        with mock.patch("jobs.notifications.send_mail", side_effect=OSError("smtp down")):
            r = self.patch("rejected")
        self.assertEqual(r.status_code, 200)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "rejected")

    def test_other_institute_cannot_change_status(self):
        other = auth(make_institute(email="o@x.com", name="Other").user)
        r = other.patch(f"/api/applications/{self.app.id}/", {"status": "hired"}, format="json")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)


class AnalyticsTests(TestCase):
    def setUp(self):
        self.inst = make_institute()
        today = timezone.localdate()
        self.j_open = make_job(self.inst, title="Open")
        self.j_expired = make_job(self.inst, title="Expired", application_deadline=today - datetime.timedelta(days=1))
        self.j_closed = make_job(self.inst, title="Closed", status="closed")
        self.j_draft = make_job(self.inst, title="Draft", status="draft")
        for i, st in enumerate(["applied", "applied", "shortlisted", "hired"]):
            JobApplication.objects.create(job=self.j_open, teacher=make_teacher(email=f"a{i}@x.com"), status=st)
        JobApplication.objects.create(job=self.j_closed, teacher=make_teacher(email="z@x.com"), status="rejected")
        # another institute's data must never leak in
        other = make_institute(email="o@x.com", name="Other")
        JobApplication.objects.create(job=make_job(other), teacher=make_teacher(email="q@x.com"), status="hired")

    def test_numbers(self):
        r = auth(self.inst.user).get("/api/institute/analytics/")
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d["total_jobs"], 4)
        self.assertEqual(d["active_jobs"], 1)          # open, not expired; closed/draft excluded
        self.assertEqual(d["total_applications"], 5)
        s = d["applications_by_status"]
        self.assertEqual((s["applied"], s["shortlisted"], s["hired"], s["rejected"], s["interview"]), (2, 1, 1, 1, 0))
        row = next(p for p in d["per_job"] if p["title"] == "Open")
        self.assertEqual((row["applications"], row["shortlisted"], row["hired"]), (4, 1, 1))

    def test_all_statuses_present_when_empty(self):
        d = auth(make_institute(email="e@x.com", name="Empty").user).get("/api/institute/analytics/").data
        self.assertEqual(d["total_applications"], 0)
        self.assertEqual(len(d["applications_by_status"]), len(JobApplication.Status.choices))

    def test_teachers_forbidden(self):
        t = make_teacher(email="tt@x.com")
        self.assertEqual(auth(t.user).get("/api/institute/analytics/").status_code, 403)

    def test_anonymous_unauthorized(self):
        self.assertEqual(APIClient().get("/api/institute/analytics/").status_code, 401)


class BackfillTests(TestCase):
    def test_backfill_scores_old_applications(self):
        inst, t = make_institute(), make_teacher()
        app = JobApplication.objects.create(job=make_job(inst), teacher=t)
        self.assertIsNone(app.match_score)
        from django.core.management import call_command
        call_command("backfill_phase2", verbosity=0)
        app.refresh_from_db()
        self.assertEqual(app.match_score, 100.0)
