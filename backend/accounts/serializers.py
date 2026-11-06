from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.db import transaction
from rest_framework import serializers

from .models import (
    Certification, EmploymentHistory, InstituteProfile, Qualification, TeacherProfile, User,
)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=["teacher", "institute"])
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    institute_name = serializers.CharField(required=False, allow_blank=True)

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
        return attrs

    @transaction.atomic
    def create(self, v):
        user = User.objects.create_user(email=v["email"], password=v["password"], role=v["role"])
        if v["role"] == "teacher":
            TeacherProfile.objects.create(
                user=user, first_name=v["first_name"], last_name=v.get("last_name", "")
            )
        else:
            InstituteProfile.objects.create(user=user, name=v["institute_name"])
        return user


class TeacherProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    completeness = serializers.IntegerField(read_only=True)

    class Meta:
        model = TeacherProfile
        exclude = ["user"]
        read_only_fields = ["created_at", "updated_at"]


class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        exclude = ["teacher"]
        read_only_fields = ["verification_status", "blockchain_tx_hash"]

    def validate_year_of_passing(self, value):
        if value < 1950 or value > 2100:
            raise serializers.ValidationError("Enter a valid year.")
        return value


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
