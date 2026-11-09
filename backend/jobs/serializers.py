from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import (
    CertificationSerializer, EmploymentHistorySerializer, QualificationSerializer,
    TeacherProfileSerializer,
)

from .models import ApplicationAnswer, JobApplication, JobPost, JobQuestion


class JobQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobQuestion
        fields = ["id", "text"]
        read_only_fields = ["id"]


class JobSerializer(serializers.ModelSerializer):
    questions = JobQuestionSerializer(many=True, required=False)
    institute_id = serializers.IntegerField(read_only=True)
    institute_name = serializers.CharField(source="institute.name", read_only=True)
    institute_verified = serializers.SerializerMethodField()
    institute_logo = serializers.ImageField(source="institute.logo", read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = JobPost
        exclude = ["institute"]
        read_only_fields = ["created_at", "updated_at"]

    def get_institute_verified(self, obj):
        return obj.institute.verification_status == "verified"

    def get_has_applied(self, obj):
        user = self.context["request"].user
        if user.role != "teacher":
            return False
        return obj.applications.filter(teacher=user.teacher_profile).exists()

    def validate(self, attrs):
        lo = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        hi = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if lo is not None and hi is not None and hi < lo:
            raise serializers.ValidationError({"salary_max": "Maximum salary must be at least the minimum."})
        qs = attrs.get("questions")
        if qs is not None and len(qs) > 5:
            raise serializers.ValidationError({"questions": "Add at most 5 application questions."})
        return attrs

    @transaction.atomic
    def create(self, validated):
        questions = validated.pop("questions", [])
        job = JobPost.objects.create(**validated)
        JobQuestion.objects.bulk_create([JobQuestion(job=job, text=q["text"]) for q in questions])
        return job

    @transaction.atomic
    def update(self, instance, validated):
        questions = validated.pop("questions", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        # Replacing questions would delete existing answers, so only allow before anyone has applied
        if questions is not None and not instance.applications.exists():
            instance.questions.all().delete()
            JobQuestion.objects.bulk_create([JobQuestion(job=instance, text=q["text"]) for q in questions])
        return instance


class AnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    answer = serializers.CharField()


class ApplySerializer(serializers.Serializer):
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    answers = AnswerInputSerializer(many=True, required=False)


class ApplicationAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)

    class Meta:
        model = ApplicationAnswer
        fields = ["question", "question_text", "answer"]


class ApplicationSerializer(serializers.ModelSerializer):
    job_id = serializers.IntegerField(read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_city = serializers.CharField(source="job.city", read_only=True)
    institute_name = serializers.CharField(source="job.institute.name", read_only=True)
    teacher_id = serializers.IntegerField(read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    answers = ApplicationAnswerSerializer(many=True, read_only=True)
    teacher_detail = serializers.SerializerMethodField()
    match_breakdown = serializers.SerializerMethodField()
    attached_qualifications = QualificationSerializer(many=True, read_only=True)
    attached_certifications = CertificationSerializer(many=True, read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id", "job_id", "job_title", "job_city", "institute_name", "teacher_id", "teacher_name",
            "status", "cover_letter", "match_score", "applied_at", "updated_at", "answers",
            "teacher_detail", "match_breakdown", "attached_qualifications", "attached_certifications",
            "interview_date", "interview_details",
        ]

    def get_match_breakdown(self, obj):
        """Why the score is what it is: institute only. Teachers just see the overall score."""
        if self.context["request"].user.role != "institute":
            return None
        return obj.match_breakdown or None

    def get_teacher_detail(self, obj):
        """Full candidate profile — only shown to the institute that received the application."""
        if self.context["request"].user.role != "institute":
            return None
        t = obj.teacher
        ctx = self.context
        return {
            "profile": TeacherProfileSerializer(t, context=ctx).data,
            "qualifications": QualificationSerializer(t.qualifications.all(), many=True, context=ctx).data,
            "employment": EmploymentHistorySerializer(t.employment.all(), many=True, context=ctx).data,
            "certifications": CertificationSerializer(t.certifications.all(), many=True, context=ctx).data,
        }


class ApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ["status"]


class ScheduleInterviewSerializer(serializers.Serializer):
    interview_date = serializers.DateTimeField()
    interview_details = serializers.CharField(required=False, allow_blank=True, max_length=300)

    def validate_interview_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Pick a date and time in the future.")
        return value
