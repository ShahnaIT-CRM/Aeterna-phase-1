import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from jobs.tests import make_institute, make_teacher
from utils import blockchain

from .models import Qualification

TMP_MEDIA = tempfile.mkdtemp()


def auth(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def pdf(content=b"%PDF-1.4 official degree"):
    return SimpleUploadedFile("degree.pdf", content, content_type="application/pdf")


class BlockchainServiceTests(TestCase):
    def test_receipt_shape_and_unique_hashes(self):
        a = blockchain.anchor_document(pdf(), issuer_id=1, subject_id=1)
        b = blockchain.anchor_document(pdf(), issuer_id=1, subject_id=1)  # same file, new transaction
        self.assertTrue(blockchain.is_valid_tx_hash(a.tx_hash))
        self.assertEqual(a.document_sha256, b.document_sha256)  # fingerprint is deterministic
        self.assertNotEqual(a.tx_hash, b.tx_hash)

    def test_file_matches_detects_tampering(self):
        r = blockchain.anchor_document(pdf(b"original"), issuer_id=1, subject_id=1)
        self.assertTrue(blockchain.file_matches(pdf(b"original"), r.document_sha256))
        self.assertFalse(blockchain.file_matches(pdf(b"forged"), r.document_sha256))


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class CredentialFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.uni = make_institute(email="uni@x.com", name="Bangalore University")
        self.uni.verification_status = "verified"
        self.uni.save()
        self.teacher = make_teacher()
        self.q = Qualification.objects.create(
            teacher=self.teacher, level="bachelors", course="B.Sc.", university="Bangalore University", year_of_passing=2015
        )
        self.url = f"/api/institute/credentials/{self.q.pk}/issue/"

    def test_issue_anchors_and_marks_verified(self):
        r = auth(self.uni.user).post(self.url, {"document": pdf()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["blockchain_verified"])
        self.assertTrue(blockchain.is_valid_tx_hash(r.data["blockchain_tx_hash"]))
        self.assertEqual(r.data["verified_by_name"], "Bangalore University")
        self.assertNotIn("issuer_document", r.data)

    def test_cannot_issue_twice(self):
        c = auth(self.uni.user)
        c.post(self.url, {"document": pdf()}, format="multipart")
        self.assertEqual(c.post(self.url, {"document": pdf()}, format="multipart").status_code, 400)

    def test_unverified_institute_is_blocked(self):
        self.uni.verification_status = "pending"
        self.uni.save()
        self.assertEqual(auth(self.uni.user).post(self.url, {"document": pdf()}, format="multipart").status_code, 403)

    def test_other_institute_cannot_issue_this_degree(self):
        other = make_institute(email="o@x.com", name="Mysore College")
        other.verification_status = "verified"
        other.save()
        self.assertEqual(auth(other.user).post(self.url, {"document": pdf()}, format="multipart").status_code, 404)

    def test_teacher_cannot_issue(self):
        self.assertEqual(auth(self.teacher.user).post(self.url, {"document": pdf()}, format="multipart").status_code, 403)

    def test_rejects_bad_file_type(self):
        bad = SimpleUploadedFile("x.exe", b"MZ")
        self.assertEqual(auth(self.uni.user).post(self.url, {"document": bad}, format="multipart").status_code, 400)

    def test_queue_lists_only_own_degrees(self):
        Qualification.objects.create(
            teacher=self.teacher, level="masters", course="M.Sc.", university="Other Univ", year_of_passing=2017
        )
        rows = auth(self.uni.user).get("/api/institute/credentials/").data
        self.assertEqual([r["id"] for r in rows], [self.q.pk])

    def test_verify_endpoint_valid_then_detects_tampering(self):
        auth(self.uni.user).post(self.url, {"document": pdf()}, format="multipart")
        self.q.refresh_from_db()
        reader = auth(make_institute(email="hr@x.com", name="Hiring School").user)
        ok = reader.get(f"/api/credentials/verify/{self.q.blockchain_tx_hash}/")
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.data["valid"])
        self.assertNotIn("teacher", str(ok.data).lower())  # no candidate identity leaked
        with open(self.q.issuer_document.path, "wb") as f:  # someone edits the stored file
            f.write(b"forged")
        self.assertFalse(reader.get(f"/api/credentials/verify/{self.q.blockchain_tx_hash}/").data["valid"])

    def test_verify_unknown_hash_404(self):
        r = auth(self.uni.user).get("/api/credentials/verify/0x" + "a" * 64 + "/")
        self.assertEqual(r.status_code, 404)

    def test_teacher_editing_the_degree_withdraws_the_proof(self):
        auth(self.uni.user).post(self.url, {"document": pdf()}, format="multipart")
        t = auth(self.teacher.user)
        t.patch(f"/api/teacher/qualifications/{self.q.pk}/", {"marks": "80"}, format="json")  # harmless edit
        self.q.refresh_from_db()
        self.assertTrue(self.q.blockchain_verified)
        t.patch(f"/api/teacher/qualifications/{self.q.pk}/", {"course": "M.Sc."}, format="json")
        self.q.refresh_from_db()
        self.assertFalse(self.q.blockchain_verified)
        self.assertEqual(self.q.blockchain_tx_hash, "")

    def test_teacher_cannot_forge_proof_fields(self):
        r = auth(self.teacher.user).patch(
            f"/api/teacher/qualifications/{self.q.pk}/",
            {"blockchain_tx_hash": "0x" + "b" * 64, "verification_status": "verified"}, format="json",
        )
        self.q.refresh_from_db()
        self.assertFalse(self.q.blockchain_verified)
