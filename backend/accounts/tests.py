import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from jobs.tests import make_degree, make_teacher, make_university
from utils import crypto

from .merit import recalculate_merit, university_points
from .models import Certification, Notification, Qualification, UniversityProfile, User

MEDIA = tempfile.mkdtemp()
PDF = b"%PDF-1.4 official degree"


def auth(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def upload(name="d.pdf", content=PDF):
    return SimpleUploadedFile(name, content)


class CryptoTests(TestCase):
    def test_sign_and_verify_roundtrip(self):
        pub, enc = crypto.generate_keypair()
        msg = b"hello"
        sig = crypto.sign_message(enc, msg)
        self.assertTrue(crypto.verify_signature(pub, msg, sig))
        self.assertFalse(crypto.verify_signature(pub, b"hellO", sig))

    def test_private_key_is_not_stored_in_clear(self):
        pub, enc = crypto.generate_keypair()
        self.assertNotIn(pub, enc)
        self.assertTrue(enc.startswith("gAAAA"))  # Fernet token

    def test_wrong_public_key_fails(self):
        _, enc = crypto.generate_keypair()
        other_pub, _ = crypto.generate_keypair()
        self.assertFalse(crypto.verify_signature(other_pub, b"m", crypto.sign_message(enc, b"m")))

    def test_message_is_deterministic(self):
        kw = dict(qualification_id=1, teacher_id=2, university_id=3, course="B.Sc", level="bachelors",
                  year_of_passing=2015, document_sha256="ab")
        self.assertEqual(crypto.build_credential_message(**kw), crypto.build_credential_message(**kw))


class UniversityKeyTests(TestCase):
    def test_keys_minted_only_on_verification(self):
        uni = make_university(verified=False)
        self.assertEqual((uni.public_key, uni.encrypted_private_key), ("", ""))
        self.assertFalse(uni.can_issue)
        uni.verification_status = "verified"
        uni.save()
        self.assertTrue(uni.public_key and uni.encrypted_private_key)
        self.assertTrue(uni.can_issue)

    def test_keys_are_not_regenerated(self):
        uni = make_university()
        pub = uni.public_key
        uni.name = "Renamed"
        uni.save()
        self.assertEqual(uni.public_key, pub)

    def test_register_university(self):
        r = APIClient().post("/api/auth/register/", {
            "email": "reg@uni.edu", "password": "Str0ng-pass-99", "role": "university",
            "university_name": "Mysore University",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["user"]["role"], "university")
        self.assertEqual(UniversityProfile.objects.get().verification_status, "pending")

    def test_dropdown_lists_only_verified_universities(self):
        make_university(email="a@x.com", name="Verified U")
        make_university(email="b@x.com", name="Pending U", verified=False)
        t = make_teacher()
        r = auth(t.user).get("/api/universities/")
        self.assertEqual([u["name"] for u in r.data], ["Verified U"])
        self.assertNotIn("public_key", r.data[0])
        self.assertEqual(len(auth(t.user).get("/api/universities/?q=zzz").data), 0)

    def test_dropdown_needs_login(self):
        self.assertEqual(APIClient().get("/api/universities/").status_code, 401)

    def test_profile_never_exposes_private_key(self):
        uni = make_university()
        r = auth(uni.user).get("/api/university/profile/")
        self.assertNotIn("encrypted_private_key", r.data)
        self.assertNotIn(uni.encrypted_private_key, str(r.data))


@override_settings(MEDIA_ROOT=MEDIA)
class DegreeFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.uni = make_university(nirf=4)
        self.teacher = make_teacher()
        self.t = auth(self.teacher.user)

    def create(self, **over):
        data = {
            "level": "phd", "course": "Ph.D. Physics", "university": self.uni.pk, "year_of_passing": 2016,
            "marksheet": upload("m.pdf"), "degree_certificate": upload("d.pdf"), **over,
        }
        data = {k: v for k, v in data.items() if v is not None}
        return self.t.post("/api/teacher/qualifications/", data, format="multipart")

    # ---- teacher side
    def test_create_notifies_the_university(self):
        r = self.create()
        self.assertEqual(r.status_code, 201, r.content)
        n = Notification.objects.get(recipient=self.uni.user)
        self.assertEqual(n.kind, "degree_request")
        self.assertIn(self.teacher.full_name, n.body)
        self.assertEqual(r.data["university_name"], self.uni.name)
        self.assertFalse(r.data["cryptographically_verified"])

    def test_both_documents_are_mandatory(self):
        self.assertEqual(self.create(marksheet=None).status_code, 400)
        self.assertEqual(self.create(degree_certificate=None).status_code, 400)

    def test_rejects_wrong_type_oversize_and_disguised_files(self):
        self.assertEqual(self.create(marksheet=upload("m.exe", b"MZ")).status_code, 400)
        self.assertEqual(self.create(marksheet=upload("m.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024))).status_code, 400)
        self.assertEqual(self.create(marksheet=upload("m.pdf", b"<script>alert(1)</script>")).status_code, 400)
        self.assertEqual(Qualification.objects.count(), 0)
        ok = self.create(marksheet=upload("m.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20))
        self.assertEqual(ok.status_code, 201, ok.content)

    def test_cannot_pick_unverified_university(self):
        pending = make_university(email="p@x.com", name="Pending U", verified=False)
        self.assertEqual(self.create(university=pending.pk).status_code, 400)

    def test_university_is_a_foreign_key_not_free_text(self):
        self.assertEqual(self.create(university="Some Random College").status_code, 400)

    def test_teacher_cannot_forge_proof_fields(self):
        q = make_degree(self.teacher, self.uni)
        self.t.patch(f"/api/teacher/qualifications/{q.pk}/",
                     {"verification_status": "verified", "signature": "x" * 88, "signed_by": self.uni.pk}, format="json")
        q.refresh_from_db()
        self.assertFalse(q.cryptographically_verified)

    # ---- university side
    def sign(self, q, user=None):
        return auth(user or self.uni.user).post(f"/api/university/requests/{q.pk}/sign/")

    def test_pending_queue_and_document_view(self):
        q = make_degree(self.teacher, self.uni)
        other_uni = make_university(email="o@x.com", name="Other U")
        make_degree(self.teacher, other_uni)
        c = auth(self.uni.user)
        rows = c.get("/api/university/requests/").data
        self.assertEqual([r["id"] for r in rows], [q.pk])
        self.assertNotIn("email", str(rows[0]).lower())
        doc = c.get(f"/api/university/requests/{q.pk}/document/degree/")
        self.assertEqual(doc.status_code, 200)
        self.assertEqual(doc["Content-Type"], "application/pdf")
        self.assertEqual(auth(other_uni.user).get(f"/api/university/requests/{q.pk}/document/degree/").status_code, 404)
        self.assertEqual(APIClient().get(f"/api/university/requests/{q.pk}/document/degree/").status_code, 401)

    def test_issue_and_sign_then_verify(self):
        q = make_degree(self.teacher, self.uni, pdf=PDF)
        r = self.sign(q)
        self.assertEqual(r.status_code, 201, r.content)
        q.refresh_from_db()
        self.assertTrue(q.cryptographically_verified)
        self.assertEqual(len(q.document_sha256), 64)
        self.assertTrue(crypto.verify_signature(self.uni.public_key, q.signing_message(), q.signature))
        self.assertTrue(Notification.objects.filter(recipient=self.teacher.user, kind="degree_signed").exists())
        v = auth(self.teacher.user).get(f"/api/credentials/verify/{q.pk}/")
        self.assertEqual(v.status_code, 200)
        self.assertTrue(v.data["valid"])
        self.assertEqual(v.data["issued_by"], self.uni.name)
        self.assertEqual(v.data["public_key"], self.uni.public_key)
        self.assertNotIn(self.teacher.full_name, str(v.data))  # candidate identity is not disclosed
        self.assertNotIn(self.teacher.user.email, str(v.data))

    def test_cannot_sign_twice(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        self.assertEqual(self.sign(q).status_code, 400)

    def test_unverified_university_cannot_sign(self):
        uni = make_university(email="p@x.com", name="Pending U", verified=False)
        q = make_degree(self.teacher, uni)
        self.assertEqual(self.sign(q, uni.user).status_code, 403)

    def test_revoked_university_cannot_sign(self):
        q = make_degree(self.teacher, self.uni)
        self.uni.is_trusted_issuer = False
        self.uni.save()
        self.assertEqual(self.sign(q).status_code, 403)

    def test_other_university_cannot_sign_this_degree(self):
        other = make_university(email="o@x.com", name="Other U")
        q = make_degree(self.teacher, self.uni)
        self.assertEqual(self.sign(q, other.user).status_code, 404)

    def test_teacher_and_institute_cannot_sign(self):
        q = make_degree(self.teacher, self.uni)
        self.assertEqual(self.sign(q, self.teacher.user).status_code, 403)

    def test_reject_notifies_teacher_and_resubmission_returns_to_pending(self):
        q = make_degree(self.teacher, self.uni)
        self.assertEqual(auth(self.uni.user).post(f"/api/university/requests/{q.pk}/reject/").status_code, 200)
        q.refresh_from_db()
        self.assertEqual(q.verification_status, "rejected")
        self.assertTrue(Notification.objects.filter(recipient=self.teacher.user, kind="degree_rejected").exists())
        self.t.patch(f"/api/teacher/qualifications/{q.pk}/", {"course": "Ph.D. (Physics)"}, format="json")
        q.refresh_from_db()
        self.assertEqual(q.verification_status, "pending")
        self.assertEqual(Notification.objects.filter(recipient=self.uni.user, kind="degree_request").count(), 1)

    # ---- tamper evidence
    def test_editing_degree_details_withdraws_the_signature(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        self.t.patch(f"/api/teacher/qualifications/{q.pk}/", {"marks": "80"}, format="json")  # not signed content
        q.refresh_from_db()
        self.assertTrue(q.cryptographically_verified)
        self.t.patch(f"/api/teacher/qualifications/{q.pk}/", {"course": "M.Sc."}, format="json")
        q.refresh_from_db()
        self.assertFalse(q.cryptographically_verified)
        self.assertEqual((q.signature, q.document_sha256), ("", ""))

    def test_replacing_the_certificate_withdraws_the_signature(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        self.t.patch(f"/api/teacher/qualifications/{q.pk}/", {"degree_certificate": upload("new.pdf", b"%PDF-1.4 x")}, format="multipart")
        q.refresh_from_db()
        self.assertFalse(q.cryptographically_verified)

    def test_db_edit_of_signed_fields_is_detected(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        Qualification.objects.filter(pk=q.pk).update(course="Ph.D. Quantum Gravity")  # sneaky direct edit
        v = auth(self.teacher.user).get(f"/api/credentials/verify/{q.pk}/").data
        self.assertFalse(v["valid"])
        self.assertEqual(v["status"], "signature_invalid")

    def test_altered_stored_file_is_detected(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        q.refresh_from_db()
        with open(q.degree_certificate.path, "wb") as f:
            f.write(b"%PDF-1.4 forged")
        v = auth(self.teacher.user).get(f"/api/credentials/verify/{q.pk}/").data
        self.assertEqual(v["status"], "document_altered")
        self.assertFalse(v["valid"])

    def test_revoking_the_issuer_invalidates_its_degrees(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        self.uni.is_trusted_issuer = False
        self.uni.save()
        self.assertEqual(auth(self.teacher.user).get(f"/api/credentials/verify/{q.pk}/").data["status"], "issuer_revoked")

    def test_signature_cannot_be_moved_to_another_degree(self):
        a = make_degree(self.teacher, self.uni, course="B.Sc.")
        b = make_degree(self.teacher, self.uni, course="M.Sc.", level="masters")
        self.sign(a)
        a.refresh_from_db()
        Qualification.objects.filter(pk=b.pk).update(
            signature=a.signature, document_sha256=a.document_sha256, signed_by=self.uni, verification_status="verified"
        )
        self.assertFalse(auth(self.teacher.user).get(f"/api/credentials/verify/{b.pk}/").data["valid"])

    # ---- verify endpoint access
    def test_unsigned_and_unknown(self):
        q = make_degree(self.teacher, self.uni)
        c = auth(self.teacher.user)
        self.assertEqual(c.get(f"/api/credentials/verify/{q.pk}/").data["status"], "unsigned")
        self.assertEqual(c.get("/api/credentials/verify/99999/").status_code, 404)

    def test_anonymous_verify_only_for_public_profiles(self):
        q = make_degree(self.teacher, self.uni)
        self.sign(q)
        anon = APIClient()
        self.assertEqual(anon.get(f"/api/credentials/verify/{q.pk}/").status_code, 404)
        self.teacher.visibility = "public"
        self.teacher.save()
        self.assertTrue(anon.get(f"/api/credentials/verify/{q.pk}/").data["valid"])


@override_settings(MEDIA_ROOT=MEDIA)
class MeritTests(TestCase):
    def setUp(self):
        self.t = make_teacher(total_experience_years=0)

    def signed(self, uni, **kw):
        q = make_degree(self.t, uni, **kw)
        r = auth(uni.user).post(f"/api/university/requests/{q.pk}/sign/")
        assert r.status_code == 201, r.content
        return q

    def merit(self):
        self.t.refresh_from_db()
        return recalculate_merit(self.t)

    def test_nirf_bands(self):
        self.assertEqual([university_points(r) for r in (1, 10, 11, 50, 51, 100, 101, 200, 201, None)],
                         [50, 50, 40, 40, 30, 30, 20, 20, 10, 5])

    def test_unsigned_degree_earns_nothing(self):
        make_degree(self.t, make_university(nirf=1), level="phd")
        m = self.merit()
        self.assertEqual(m.breakdown["university"] + m.breakdown["degree"], 0)

    def test_laureate_example(self):
        self.t.total_experience_years = 10
        self.t.save()
        self.signed(make_university(nirf=4), level="phd", course="Ph.D.")
        Certification.objects.create(teacher=self.t, name="CTET", verification_status="verified")
        m = self.merit()
        self.assertEqual(m.breakdown, {"university": 50, "degree": 25, "certification": 15, "experience": 10})
        self.assertEqual((m.score, m.tier), (100, "laureate"))
        self.assertEqual(m.headline, "Aeterna Laureate — Elite-tier educator. PhD from NIRF Rank #4 University.")

    def test_tier_boundaries(self):
        from .merit import tier_for
        self.assertEqual([tier_for(s)[0] for s in (100, 90, 89, 80, 79, 70, 69, 60, 59, 0)],
                         ["laureate", "laureate", "distinguished", "distinguished", "fellow", "fellow",
                          "associate", "associate", "emerging", "emerging"])

    def test_unverified_certificate_does_not_count(self):
        Certification.objects.create(teacher=self.t, name="NET")  # pending
        self.assertEqual(self.merit().breakdown["certification"], 0)

    def test_tefl_and_aliases(self):
        Certification.objects.create(teacher=self.t, name="TEFL", verification_status="verified")
        self.assertEqual(self.merit().breakdown["certification"], 5)
        Certification.objects.create(teacher=self.t, name="UGC-NET", verification_status="verified")
        self.assertEqual(self.merit().breakdown["certification"], 15)

    def test_experience_capped_at_10(self):
        self.t.total_experience_years = 25
        self.t.save()
        self.assertEqual(self.merit().breakdown["experience"], 10)

    def test_score_follows_signing_and_university_rank_change(self):
        uni = make_university(nirf=120)
        self.signed(uni, level="masters", course="M.Sc.")
        self.assertEqual(self.merit().score, 20 + 20)
        uni.nirf_rank = 8
        uni.save()
        self.assertEqual(self.merit().score, 50 + 20)

    def test_best_degree_uses_one_degree_for_both_parts(self):
        self.signed(make_university(email="a@x.com", name="A", nirf=5), level="bachelors", course="B.Sc.")
        self.signed(make_university(email="b@x.com", name="B", nirf=None), level="phd", course="Ph.D.")
        m = self.merit()
        self.assertEqual((m.breakdown["university"], m.breakdown["degree"]), (50, 15))  # 65 beats 5 + 25

    def test_tier_up_notifies_teacher_and_profile_exposes_progress(self):
        with self.captureOnCommitCallbacks(execute=True):  # the app recalculates after commit
            self.t.total_experience_years = 10
            self.t.save()  # first score: Emerging
        with self.captureOnCommitCallbacks(execute=True):
            self.signed(make_university(nirf=30), level="masters", course="M.Sc.")  # 40 + 20 + 10 = 70
        self.assertTrue(Notification.objects.filter(recipient=self.t.user, kind="tier_up").exists())
        m = auth(self.t.user).get("/api/teacher/profile/").data["merit"]
        self.assertEqual((m["score"], m["tier"]), (70, "fellow"))
        self.assertEqual(m["next_tier"]["next_tier_name"], "Distinguished Scholar")
        self.assertEqual(m["next_tier"]["points_needed"], 10)
        self.assertTrue(any("CTET" in s["action"] for s in m["next_steps"]))

    def test_next_steps_suggest_getting_pending_degree_signed(self):
        uni = make_university(nirf=3)
        make_degree(self.t, uni, level="phd")
        m = auth(self.t.user).get("/api/teacher/profile/").data["merit"]
        self.assertEqual(m["next_steps"][0]["points"], 75)
        self.assertIn(uni.name, m["next_steps"][0]["action"])


@override_settings(MEDIA_ROOT=MEDIA)
class PublicProfileTests(TestCase):
    def setUp(self):
        self.uni = make_university(nirf=4)
        self.t = make_teacher(phone="9999999999", visibility="public")
        self.q = make_degree(self.t, self.uni, level="phd", course="Ph.D.")
        auth(self.uni.user).post(f"/api/university/requests/{self.q.pk}/sign/")
        make_degree(self.t, self.uni, course="Unsigned course")

    def test_public_page_shows_only_verified_and_no_private_data(self):
        r = APIClient().get(f"/api/public/teachers/{self.t.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([q["course"] for q in r.data["qualifications"]], ["Ph.D."])
        self.assertEqual((r.data["merit"]["score"], r.data["merit"]["tier"]), (80, "distinguished"))  # 50+25+5 exp
        flat = str(r.data)
        for secret in ("9999999999", "t@x.com", "marksheet", "degree_certificate", "salary"):
            self.assertNotIn(secret, flat)

    def test_non_public_profile_is_404(self):
        self.t.visibility = "selective"
        self.t.save()
        self.assertEqual(APIClient().get(f"/api/public/teachers/{self.t.pk}/").status_code, 404)

    def test_stale_token_does_not_break_public_page(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(c.get(f"/api/public/teachers/{self.t.pk}/").status_code, 200)


class NotificationTests(TestCase):
    def test_list_read_and_isolation(self):
        a, b = make_university(email="a@x.com", name="A"), make_university(email="b@x.com", name="B")
        n = Notification.objects.create(recipient=a.user, kind="degree_request", title="Hi")
        c = auth(a.user)
        self.assertEqual(c.get("/api/notifications/").data["unread_count"], 1)
        self.assertEqual(auth(b.user).get("/api/notifications/").data["unread_count"], 0)
        auth(b.user).post(f"/api/notifications/{n.pk}/read/")  # someone else's: ignored
        self.assertEqual(c.get("/api/notifications/").data["unread_count"], 1)
        c.post(f"/api/notifications/{n.pk}/read/")
        self.assertEqual(c.get("/api/notifications/").data["unread_count"], 0)
