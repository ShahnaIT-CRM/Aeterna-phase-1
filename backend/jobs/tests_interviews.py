from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import JobApplication
from .tests import auth, make_institute, make_job, make_teacher


def future(hours=48):
    return (timezone.now() + timedelta(hours=hours)).isoformat()


class InterviewSchedulerTests(TestCase):
    def setUp(self):
        self.inst = make_institute()
        self.teacher = make_teacher()
        self.app = JobApplication.objects.create(job=make_job(self.inst), teacher=self.teacher)
        self.url = f"/api/applications/{self.app.pk}/schedule-interview/"
        self.c = auth(self.inst.user)

    def test_schedule_sets_status_date_and_emails_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.c.post(self.url, {"interview_date": future(), "interview_details": "Room 4"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "interview")
        self.assertEqual(self.app.interview_details, "Room 4")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Room 4", mail.outbox[0].body)
        self.assertIn("scheduled", mail.outbox[0].subject)

    def test_reschedule_sends_rescheduled_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.c.post(self.url, {"interview_date": future(48)}, format="json")
            self.c.post(self.url, {"interview_date": future(72)}, format="json")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("rescheduled", mail.outbox[1].subject)

    def test_past_date_rejected(self):
        r = self.c.post(self.url, {"interview_date": future(-2)}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("interview_date", r.data)

    def test_missing_date_rejected(self):
        self.assertEqual(self.c.post(self.url, {}, format="json").status_code, 400)

    def test_blocked_for_rejected_and_hired(self):
        for st in ("rejected", "hired", "offered"):
            JobApplication.objects.filter(pk=self.app.pk).update(status=st)
            self.assertEqual(self.c.post(self.url, {"interview_date": future()}, format="json").status_code, 400, st)

    def test_other_institute_gets_404_and_teacher_403(self):
        other = auth(make_institute(email="o@x.com", name="Other").user)
        self.assertEqual(other.post(self.url, {"interview_date": future()}, format="json").status_code, 404)
        self.assertEqual(auth(self.teacher.user).post(self.url, {"interview_date": future()}, format="json").status_code, 403)

    def test_double_booking_same_candidate_blocked(self):
        other_inst = make_institute(email="o@x.com", name="Other")
        other_app = JobApplication.objects.create(job=make_job(other_inst), teacher=self.teacher)
        auth(other_inst.user).post(f"/api/applications/{other_app.pk}/schedule-interview/",
                                   {"interview_date": future(48)}, format="json")
        r = self.c.post(self.url, {"interview_date": future(48.5)}, format="json")  # 30 min later
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.post(self.url, {"interview_date": future(50)}, format="json").status_code, 200)

    def test_rescheduling_does_not_clash_with_itself(self):
        self.c.post(self.url, {"interview_date": future(48)}, format="json")
        self.assertEqual(self.c.post(self.url, {"interview_date": future(48.25)}, format="json").status_code, 200)

    def test_teacher_sees_only_own_upcoming_interviews_in_order(self):
        self.c.post(self.url, {"interview_date": future(96)}, format="json")
        a2 = JobApplication.objects.create(job=make_job(self.inst, title="TGT"), teacher=self.teacher)
        self.c.post(f"/api/applications/{a2.pk}/schedule-interview/", {"interview_date": future(24)}, format="json")
        past = JobApplication.objects.create(job=make_job(self.inst, title="Old"), teacher=self.teacher,
                                             status="interview", interview_date=timezone.now() - timedelta(days=1))
        stranger = make_teacher(email="s@x.com")
        JobApplication.objects.create(job=make_job(self.inst, title="Other"), teacher=stranger,
                                      status="interview", interview_date=timezone.now() + timedelta(days=1))
        rows = auth(self.teacher.user).get("/api/applications/interviews/").data
        self.assertEqual([r["job_title"] for r in rows], ["TGT", "PGT Physics"])
        self.assertNotIn(past.pk, [r["id"] for r in rows])

    def test_application_serializer_exposes_interview_fields(self):
        self.c.post(self.url, {"interview_date": future()}, format="json")
        row = auth(self.teacher.user).get("/api/applications/").data[0]
        self.assertIsNotNone(row["interview_date"])
