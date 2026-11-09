from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from utils import blockchain

from .models import Certification, EmploymentHistory, Qualification, VerificationStatus
from .permissions import IsInstitute, IsTeacher
from .serializers import (
    CertificationSerializer, EmploymentHistorySerializer, InstituteProfileSerializer,
    IssuerCredentialSerializer, QualificationSerializer, RegisterSerializer, TeacherProfileSerializer,
)


def user_payload(user):
    if user.role == "teacher":
        name = user.teacher_profile.full_name
    elif user.role == "institute":
        name = user.institute_profile.name
    else:
        name = "Admin"
    return {"id": user.id, "email": user.email, "role": user.role, "display_name": name}


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"user": user_payload(user), "access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    def get(self, request):
        return Response(user_payload(request.user))


class TeacherProfileView(RetrieveUpdateAPIView):
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsTeacher]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        return self.request.user.teacher_profile


class InstituteProfileView(RetrieveUpdateAPIView):
    serializer_class = InstituteProfileSerializer
    permission_classes = [IsInstitute]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        return self.request.user.institute_profile


class _TeacherOwnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacher]
    model = None

    def get_queryset(self):
        return self.model.objects.filter(teacher=self.request.user.teacher_profile)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher_profile)


class QualificationViewSet(_TeacherOwnedViewSet):
    model = Qualification
    serializer_class = QualificationSerializer


class CertificationViewSet(_TeacherOwnedViewSet):
    model = Certification
    serializer_class = CertificationSerializer


class EmploymentViewSet(_TeacherOwnedViewSet):
    model = EmploymentHistory
    serializer_class = EmploymentHistorySerializer


# ---------------------------------------------------------------- Phase 3: blockchain credentials
MAX_CREDENTIAL_BYTES = 10 * 1024 * 1024
CREDENTIAL_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")


def issuer_qualifications(institute):
    """Degrees that name this institute as the awarding university (case-insensitive substring match).

    One rule for both the queue and the issue endpoint, so an institute can only ever anchor a degree
    it can also see. Only admin-verified institutes may issue at all (checked in the views).
    """
    if not institute.name.strip():
        return Qualification.objects.none()
    return Qualification.objects.select_related("teacher").filter(university__icontains=institute.name.strip())


class CredentialQueueView(APIView):
    """GET /api/institute/credentials/: degrees that name this institute, pending ones first."""

    permission_classes = [IsInstitute]

    def get(self, request):
        qs = issuer_qualifications(request.user.institute_profile).order_by("blockchain_tx_hash", "-year_of_passing")
        return Response(IssuerCredentialSerializer(qs, many=True, context={"request": request}).data)


class IssueCredentialView(APIView):
    """POST /api/institute/credentials/<id>/issue/ (multipart, field `document`).

    The institute uploads its official digital copy; we fingerprint it, "write" it to the mock chain
    and mark the degree blockchain-verified.
    """

    permission_classes = [IsInstitute]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        inst = request.user.institute_profile
        if inst.verification_status != VerificationStatus.VERIFIED:
            raise PermissionDenied("Your institute must be verified by Aeterna before it can issue credentials.")
        doc = request.FILES.get("document")
        if not doc:
            raise ValidationError({"document": "Upload the official certificate file."})
        if not doc.name.lower().endswith(CREDENTIAL_EXTENSIONS):
            raise ValidationError({"document": "Upload a PDF, PNG or JPG file."})
        if doc.size > MAX_CREDENTIAL_BYTES:
            raise ValidationError({"document": "File is too large (10 MB maximum)."})

        with transaction.atomic():
            q = get_object_or_404(issuer_qualifications(inst).select_for_update(of=("self",)), pk=pk)
            if q.blockchain_tx_hash:
                raise ValidationError({"detail": "This degree has already been anchored."})
            receipt = blockchain.anchor_document(doc, issuer_id=inst.pk, subject_id=q.pk)
            q.issuer_document = doc
            q.blockchain_tx_hash = receipt.tx_hash
            q.document_sha256 = receipt.document_sha256
            q.blockchain_block = receipt.block_number
            q.verified_at = receipt.anchored_at
            q.verified_by = inst
            q.verification_status = VerificationStatus.VERIFIED
            q.save()
        return Response(IssuerCredentialSerializer(q, context={"request": request}).data, status=201)


class VerifyCredentialView(APIView):
    """GET /api/credentials/verify/<tx_hash>/: the "click a link, see a tamper-proof certificate" check.

    Any signed-in user may call it, but the 64-hex hash is only ever shown on a candidate's application
    or profile, and the response leaves out who the teacher is.
    """

    def get(self, request, tx_hash):
        tx_hash = tx_hash.lower()
        q = Qualification.objects.select_related("verified_by").filter(blockchain_tx_hash=tx_hash).first()
        if not blockchain.is_valid_tx_hash(tx_hash) or not q:
            return Response({"valid": False, "detail": "No record found for this transaction."}, status=404)
        intact = bool(q.issuer_document) and blockchain.file_matches(q.issuer_document, q.document_sha256)
        return Response(
            {
                "valid": intact,
                "tx_hash": q.blockchain_tx_hash,
                "network": blockchain.NETWORK,
                "block_number": q.blockchain_block,
                "anchored_at": q.verified_at,
                "issued_by": q.verified_by.name if q.verified_by else None,
                "course": q.course,
                "university": q.university,
                "year_of_passing": q.year_of_passing,
                "document_intact": intact,
            }
        )
