from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.db import transaction
from rest_framework import serializers

from . import merit as merit_engine
from . import notifications
from .models import (
    Certification, EmploymentHistory, InstituteProfile, Notification, Qualification, TeacherMeritScore,
    TeacherProfile, UniversityProfile, User, VerificationStatus,
)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=["teacher", "institute", "university"])
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    institute_name = serializers.CharField(required=False, allow_blank=True)
    university_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        run_password_validators(value)
        return value

    def validate(self, attrs):
        if attrs["role"] == "teacher" and not attrs.get("first_name"):
            raise serializers.ValidationError({"first_name": "First name is required."})
        if attrs["role"] == "institute" and not attrs.get("institute_name"):
            raise serializers.ValidationError({"institute_name": "Institute name is required."})
        if attrs["role"] == "university":
            name = (attrs.get("university_name") or "").strip()
            if not name:
                raise serializers.ValidationError({"university_name": "University name is required."})
            if UniversityProfile.objects.filter(name__iexact=name).exists():
                raise serializers.ValidationError(
                    {"university_name": "A university with this name already exists. Contact Aeterna to claim it."}
                )
            attrs["university_name"] = name
        return attrs

    @transaction.atomic
    def create(self, v):
        user = User.objects.create_user(email=v["email"], password=v["password"], role=v["role"])
        if v["role"] == "teacher":
            TeacherProfile.objects.create(
                user=user, first_name=v["first_name"], last_name=v.get("last_name", "")
            )
        elif v["role"] == "university":
            UniversityProfile.objects.create(user=user, name=v["university_name"])
        else:
            InstituteProfile.objects.create(user=user, name=v["institute_name"])
        return user


class TeacherMeritSerializer(serializers.ModelSerializer):
    tier_name = serializers.CharField(source="get_tier_display", read_only=True)

    class Meta:
        model = TeacherMeritScore
        fields = ["score", "tier", "tier_name", "headline", "breakdown", "calculated_at"]


def merit_payload(teacher, include_progress=True):
    """Stored score (created on first read for teachers who pre-date Phase 4) plus, for the owner,
    the distance to the next tier and the actions that would close it."""
    obj = getattr(teacher, "merit", None) or merit_engine.recalculate_merit(teacher)
    data = TeacherMeritSerializer(obj).data
    if include_progress:
        data["next_tier"] = merit_engine.next_tier_info(obj.score)
        data["next_steps"] = merit_engine.next_steps(teacher, obj.breakdown)
        data["max_points"] = {
            "university": merit_engine.UNIVERSITY_MAX, "degree": merit_engine.DEGREE_MAX,
            "certification": merit_engine.CERT_MAX, "experience": merit_engine.EXPERIENCE_MAX,
        }
    return data


class TeacherProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    completeness = serializers.IntegerField(read_only=True)
    merit = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        exclude = ["user"]
        read_only_fields = ["created_at", "updated_at"]

    def get_merit(self, obj):
        return merit_payload(obj)


class UniversityOptionSerializer(serializers.ModelSerializer):
    """What the teacher's dropdown needs. Nothing about keys."""

    class Meta:
        model = UniversityProfile
        fields = ["id", "name", "city", "state", "nirf_rank"]


class QualificationSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(
        queryset=UniversityProfile.objects.filter(
            verification_status=VerificationStatus.VERIFIED, is_trusted_issuer=True
        ).exclude(public_key="")
    )
    university_name = serializers.CharField(source="university.name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    cryptographically_verified = serializers.BooleanField(read_only=True)
    signed_by_name = serializers.CharField(source="signed_by.name", read_only=True, default=None)

    # A signature covers exactly these fields plus the certificate file. Changing any of them would make
    # the proof describe a different degree, so the proof is withdrawn and the university must sign again.
    PROOF_FIELDS = ("level", "course", "university", "year_of_passing", "degree_certificate")
    DOC_FIELDS = ("marksheet", "degree_certificate")

    class Meta:
        model = Qualification
        exclude = ["teacher"]
        read_only_fields = [
            "verification_status", "document_sha256", "signature", "signed_by", "signed_at", "created_at",
        ]

    def validate(self, attrs):
        # Both documents are mandatory. DRF enforces it on create; this also catches old rows that
        # were saved before the rule existed and are now being edited without a file.
        errors = {}
        for f in self.DOC_FIELDS:
            if not attrs.get(f) and not (self.instance and getattr(self.instance, f)):
                errors[f] = "This document is required."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_year_of_passing(self, value):
        if value < 1950 or value > 2100:
            raise serializers.ValidationError("Enter a valid year.")
        return value

    @transaction.atomic
    def create(self, validated):
        q = super().create(validated)
        notifications.notify_degree_request(q)
        return q

    @transaction.atomic
    def update(self, instance, validated):
        changed = any(f in validated and validated[f] != getattr(instance, f) for f in self.PROOF_FIELDS)
        if changed:
            instance.clear_signature()  # back to pending, even after a rejection
        q = super().update(instance, validated)
        if changed:
            notifications.notify_degree_request(q)  # re-submitted to the (possibly new) university
        return q


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        exclude = ["teacher"]
        read_only_fields = ["verification_status"]


class EmploymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentHistory
        exclude = ["teacher"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        current = attrs.get("is_current", getattr(self.instance, "is_current", False))
        if current:
            attrs["end_date"] = None
        elif end and start and end < start:
            raise serializers.ValidationError({"end_date": "End date must be after the start date."})
        return attrs


class InstituteProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = InstituteProfile
        exclude = ["user"]
        read_only_fields = [
            "verification_status", "subscription_plan", "job_post_quota", "created_at",
        ]


class UniversityProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True, default=None)
    can_issue = serializers.BooleanField(read_only=True)
    key_fingerprint = serializers.CharField(read_only=True)

    class Meta:
        model = UniversityProfile
        fields = [
            "id", "name", "email", "city", "state", "website", "logo", "verification_status",
            "is_trusted_issuer", "nirf_rank", "public_key", "key_fingerprint", "can_issue",
        ]
        read_only_fields = ["name", "verification_status", "is_trusted_issuer", "nirf_rank", "public_key"]


class DegreeRequestSerializer(serializers.ModelSerializer):
    """What a university sees in its dashboard queue. Contains no contact details of the teacher."""
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Qualification
        fields = [
            "id", "teacher_name", "level", "level_label", "course", "specialization", "year_of_passing",
            "grading_system", "marks", "verification_status", "created_at", "signed_at",
            "document_sha256", "signature",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "is_read", "created_at"]
