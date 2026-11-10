import html
import mimetypes
import re

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from utils import crypto

from . import notifications
from .models import (
    Certification, EmploymentHistory, Notification, Qualification, TeacherProfile, UniversityProfile,
    VerificationStatus,
)
from .permissions import IsInstitute, IsTeacher, IsUniversity
from .serializers import (
    CertificationSerializer, DegreeRequestSerializer, EmploymentHistorySerializer, InstituteProfileSerializer,
    NotificationSerializer, QualificationSerializer, RegisterSerializer, TeacherProfileSerializer,
    UniversityOptionSerializer, UniversityProfileSerializer, merit_payload,
)


def user_payload(user):
    if user.role == "teacher":
        name = user.teacher_profile.full_name
    elif user.role == "institute":
        name = user.institute_profile.name
    elif user.role == "university":
        name = user.university_profile.name
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


class UniversityProfileView(RetrieveUpdateAPIView):
    serializer_class = UniversityProfileSerializer
    permission_classes = [IsUniversity]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user.university_profile


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


# ---------------------------------------------------------------- Phase 4: universities, PKI, merit
class UniversityListView(ListAPIView):
    """GET /api/universities/?q=: verified universities for the teacher's searchable dropdown."""

    serializer_class = UniversityOptionSerializer
    pagination_class = None

    def get_queryset(self):
        qs = UniversityProfile.objects.filter(
            verification_status=VerificationStatus.VERIFIED, is_trusted_issuer=True
        ).exclude(public_key="")
        q = self.request.query_params.get("q", "").strip()
        return qs.filter(name__icontains=q) if q else qs


class SigningUnavailable(APIException):
    status_code = 503
    default_detail = "The signing key is temporarily unavailable. Please try again later."


class _UniversityRequestMixin:
    permission_classes = [IsUniversity]

    def own_requests(self):
        return Qualification.objects.select_related("teacher", "university").filter(
            university=self.request.user.university_profile
        )


class DegreeRequestListView(_UniversityRequestMixin, APIView):
    """GET /api/university/requests/?status=pending|signed|rejected (default pending)."""

    def get(self, request):
        qs = self.own_requests()
        want = request.query_params.get("status", "pending")
        if want == "signed":
            qs = qs.exclude(signature="").order_by("-signed_at")
        elif want == "rejected":
            qs = qs.filter(verification_status=VerificationStatus.REJECTED).order_by("-created_at")
        else:
            qs = qs.filter(signature="", verification_status=VerificationStatus.PENDING).order_by("created_at")
        return Response(DegreeRequestSerializer(qs, many=True).data)


class DegreeRequestDocumentView(_UniversityRequestMixin, APIView):
    """GET /api/university/requests/<id>/document/<degree|marksheet>/: the teacher's upload, only to the
    university the degree names, and only with a valid login (so the file is never an open link)."""

    def get(self, request, pk, which):
        field = {"degree": "degree_certificate", "marksheet": "marksheet"}.get(which)
        if not field:
            raise Http404
        q = get_object_or_404(self.own_requests(), pk=pk)
        f = getattr(q, field)
        if not f:
            raise Http404
        try:
            fh = f.open("rb")
        except OSError:
            raise Http404
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        resp = FileResponse(fh, content_type=ctype)
        resp["Content-Disposition"] = f'inline; filename="{which}{f.name[f.name.rfind("."):]}"'
        resp["X-Content-Type-Options"] = "nosniff"
        return resp


class SignDegreeView(_UniversityRequestMixin, APIView):
    """POST /api/university/requests/<id>/sign/: "Issue & Sign".

    SHA-256 of the teacher's degree certificate, then an Ed25519 signature over the canonical credential
    message (which contains that hash), made with the university's private key.
    """

    def post(self, request, pk):
        uni = request.user.university_profile
        if not uni.can_issue:
            raise PermissionDenied("Your university must be verified by Aeterna before it can sign degrees.")
        with transaction.atomic():
            q = get_object_or_404(self.own_requests().select_for_update(of=("self",)), pk=pk)
            if q.signature:
                raise ValidationError({"detail": "This degree has already been signed."})
            if not q.degree_certificate:
                raise ValidationError({"detail": "The teacher has not uploaded a degree certificate."})
            try:
                q.document_sha256 = crypto.sha256_of_file(q.degree_certificate)
            except OSError:
                raise ValidationError({"detail": "The certificate file could not be read."})
            message = q.signing_message()
            try:
                signature = crypto.sign_message(uni.encrypted_private_key, message)
            except crypto.KeyDecryptionError:
                raise SigningUnavailable()
            if not crypto.verify_signature(uni.public_key, message, signature):  # self-check before saving
                raise SigningUnavailable()
            q.signature = signature
            q.signed_by = uni
            q.signed_at = timezone.now()
            q.verification_status = VerificationStatus.VERIFIED
            q.save()
            notifications.notify_degree_signed(q)
        return Response(DegreeRequestSerializer(q).data, status=201)


class RejectDegreeView(_UniversityRequestMixin, APIView):
    """POST /api/university/requests/<id>/reject/: the university cannot confirm this degree."""

    def post(self, request, pk):
        with transaction.atomic():
            q = get_object_or_404(self.own_requests().select_for_update(of=("self",)), pk=pk)
            if q.signature:
                raise ValidationError({"detail": "A signed degree cannot be rejected."})
            q.verification_status = VerificationStatus.REJECTED
            q.save(update_fields=["verification_status"])
            notifications.notify_degree_rejected(q)
        return Response(DegreeRequestSerializer(q).data)


class VerifyCredentialView(APIView):
    """GET /api/credentials/verify/<qualification_id>/: re-check a signed degree from scratch.

    Re-hashes the stored certificate, rebuilds the signed message from the database record and checks the
    Ed25519 signature with the university's public key. Visitors who are not signed in can only check
    degrees of teachers whose profile is public. The response never says who the teacher is.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        q = Qualification.objects.select_related("university", "signed_by", "teacher").filter(pk=pk).first()
        if not q or not (q.teacher.visibility == TeacherProfile.Visibility.PUBLIC or request.user.is_authenticated):
            return Response({"valid": False, "status": "not_found", "detail": "No record found."}, status=404)
        if not q.signature or not q.signed_by:
            return Response({"valid": False, "status": "unsigned", "detail": "This degree has not been signed by its university."})

        signer = q.signed_by
        signature_ok = signer.id == q.university_id and crypto.verify_signature(
            signer.public_key, q.signing_message(), q.signature
        )
        intact = bool(q.degree_certificate) and crypto.file_matches(q.degree_certificate, q.document_sha256)
        trusted = signer.is_trusted_issuer and signer.verification_status == VerificationStatus.VERIFIED
        if not signature_ok:
            state = "signature_invalid"
        elif not intact:
            state = "document_altered"
        elif not trusted:
            state = "issuer_revoked"
        else:
            state = "valid"
        return Response({
            "valid": state == "valid",
            "status": state,
            "signature_valid": signature_ok,
            "document_intact": intact,
            "issuer_trusted": trusted,
            "algorithm": crypto.ALGORITHM,
            "issued_by": signer.name,
            "issuer_nirf_rank": signer.nirf_rank,
            "key_fingerprint": signer.key_fingerprint,
            "public_key": signer.public_key,
            "signature": q.signature,
            "document_sha256": q.document_sha256,
            "signed_message": q.signing_message().decode(),
            "signed_at": q.signed_at,
            "course": q.course,
            "level": q.level,
            "year_of_passing": q.year_of_passing,
            "university": q.university.name,
        })


# ---------------------------------------------------------------- notifications (bell dropdown)
class NotificationListView(APIView):
    """GET /api/notifications/ -> {unread_count, results: latest 20}."""

    def get(self, request):
        mine = Notification.objects.filter(recipient=request.user)
        return Response({
            "unread_count": mine.filter(is_read=False).count(),
            "results": NotificationSerializer(mine[:20], many=True).data,
        })


class NotificationReadView(APIView):
    def post(self, request, pk):
        Notification.objects.filter(recipient=request.user, pk=pk).update(is_read=True)
        return Response(status=204)


class NotificationReadAllView(APIView):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response(status=204)


# ---------------------------------------------------------------- public prestige profile
def _public_teacher(teacher_id):
    return get_object_or_404(
        TeacherProfile.objects.select_related("merit"), pk=teacher_id, visibility=TeacherProfile.Visibility.PUBLIC
    )


class PublicTeacherView(APIView):
    """GET /api/public/teachers/<id>/: the shareable certificate page. Only teachers who set their profile
    to Public. No contact details, date of birth, address, marks or document files are ever included."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, teacher_id):
        t = _public_teacher(teacher_id)
        degrees = [
            q for q in t.qualifications.select_related("university")
            if q.cryptographically_verified
        ]
        return Response({
            "id": t.id,
            "name": t.full_name,
            "photo": request.build_absolute_uri(t.photo.url) if t.photo else None,
            "headline": t.headline,
            "city": t.city,
            "state": t.state,
            "total_experience_years": t.total_experience_years,
            "subjects": t.subjects,
            "merit": merit_payload(t, include_progress=False),
            "qualifications": [
                {
                    "id": q.id, "course": q.course, "specialization": q.specialization,
                    "level": q.level, "level_label": q.get_level_display(), "year_of_passing": q.year_of_passing,
                    "university_name": q.university.name, "nirf_rank": q.university.nirf_rank,
                    "cryptographically_verified": True,
                }
                for q in degrees
            ],
            "certifications": [
                {"name": c.name, "issuing_organization": c.issuing_organization}
                for c in t.certifications.filter(verification_status=VerificationStatus.VERIFIED)
            ],
            "employment": [
                {
                    "designation": e.designation, "institute_name": e.institute_name,
                    "start_date": e.start_date, "end_date": e.end_date, "is_current": e.is_current,
                }
                for e in t.employment.all()[:6]
            ],
            "member_since": t.created_at,
        })


def public_profile_shell(request, teacher_id):
    """GET /t/<id>: the React app's index.html with Open Graph tags filled in, so LinkedIn, WhatsApp and
    friends show a proper preview card (they do not run JavaScript)."""
    try:
        page = render_to_string("index.html", request=request)
    except TemplateDoesNotExist:
        raise Http404
    t = TeacherProfile.objects.select_related("merit").filter(
        pk=teacher_id, visibility=TeacherProfile.Visibility.PUBLIC
    ).first()
    if t and getattr(t, "merit", None):
        title = f"{t.full_name} · {t.merit.get_tier_display()} | Aeterna"
        desc = t.merit.headline
        base = settings.SITE_URL.rstrip("/")
        tags = [
            ("og:type", "profile"), ("og:title", title), ("og:description", desc),
            ("og:url", f"{base}/t/{t.id}"), ("og:site_name", "Aeterna"),
        ]
        if t.photo:
            tags.append(("og:image", base + t.photo.url))
        meta = "".join(f'<meta property="{k}" content="{html.escape(v, quote=True)}">' for k, v in tags)
        meta += f'<meta name="description" content="{html.escape(desc, quote=True)}">'
        page = re.sub(r"<title>.*?</title>", lambda _: f"<title>{html.escape(title)}</title>", page, count=1, flags=re.S)
        page = page.replace("</head>", meta + "</head>", 1)
    return HttpResponse(page)
