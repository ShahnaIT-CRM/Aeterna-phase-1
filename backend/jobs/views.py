from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounts.permissions import IsInstitute, IsTeacher

from .models import ApplicationAnswer, JobApplication, JobPost
from .notifications import notify_status_change
from .serializers import (
    ApplicationSerializer, ApplicationStatusSerializer, ApplySerializer, JobSerializer,
)


class JobPagination(PageNumberPagination):
    page_size = 12


class JobViewSet(viewsets.ModelViewSet):
    """
    Teachers: browse open jobs (with filters) and apply.
    Institutes: full CRUD on their own jobs.
    """

    serializer_class = JobSerializer
    pagination_class = JobPagination

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsInstitute()]
        if self.action == "apply":
            return [IsTeacher()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = JobPost.objects.select_related("institute").annotate(applications_count=Count("applications")).order_by("-created_at")
        if user.role == "institute":
            qs = qs.filter(institute=user.institute_profile)
        elif user.role == "teacher":
            qs = qs.filter(status="open").exclude(application_deadline__lt=timezone.localdate())
        p = self.request.query_params
        if p.get("q"):
            q = p["q"]
            qs = qs.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(specialization__icontains=q)
                | Q(designation__icontains=q) | Q(department__icontains=q) | Q(institute__name__icontains=q)
            )
        for field in ("employment_type", "work_mode", "curriculum", "designation"):
            if p.get(field):
                qs = qs.filter(**{f"{field}__iexact": p[field]})
        if p.get("city"):
            qs = qs.filter(city__icontains=p["city"])
        if p.get("max_experience") not in (None, ""):
            qs = qs.filter(min_experience_years__lte=int(p["max_experience"]))
        return qs

    def perform_create(self, serializer):
        inst = self.request.user.institute_profile
        if inst.job_post_quota <= 0:
            raise serializers.ValidationError(
                {"detail": "You have used all your job posts. Contact us to upgrade your plan."}
            )
        serializer.save(institute=inst)
        inst.job_post_quota -= 1
        inst.save(update_fields=["job_post_quota"])

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        job = self.get_object()
        teacher = request.user.teacher_profile
        if job.applications.filter(teacher=teacher).exists():
            raise serializers.ValidationError({"detail": "You have already applied to this job."})
        s = ApplySerializer(data=request.data)
        s.is_valid(raise_exception=True)

        answers = {a["question"]: a["answer"].strip() for a in s.validated_data.get("answers", [])}
        questions = list(job.questions.all())
        missing = [q.text for q in questions if not answers.get(q.id)]
        if missing:
            raise serializers.ValidationError({"answers": "Please answer all application questions."})

        app = JobApplication.objects.create(
            job=job, teacher=teacher, cover_letter=s.validated_data.get("cover_letter", "")
        )
        ApplicationAnswer.objects.bulk_create(
            [ApplicationAnswer(application=app, question=q, answer=answers[q.id]) for q in questions]
        )
        return Response(
            ApplicationSerializer(app, context=self.get_serializer_context()).data, status=201
        )


class ApplicationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Teachers: their own applications. Institutes: applications to their jobs (+ status updates)."""

    serializer_class = ApplicationSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "partial_update":
            return [IsInstitute()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = JobApplication.objects.select_related("job__institute", "teacher").prefetch_related(
            "answers__question"
        )
        if user.role == "teacher":
            qs = qs.filter(teacher=user.teacher_profile)
        elif user.role == "institute":
            qs = qs.filter(job__institute=user.institute_profile)
        else:
            qs = qs.none()
        if self.request.query_params.get("job"):
            qs = qs.filter(job_id=self.request.query_params["job"])
        return qs

    def partial_update(self, request, *args, **kwargs):
        app = self.get_object()
        s = ApplicationStatusSerializer(app, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        notify_status_change(app)
        return Response(ApplicationSerializer(app, context=self.get_serializer_context()).data)
