import logging

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsInstitute, IsTeacher

from .matching import compute_match_breakdown
from .models import ApplicationAnswer, JobApplication, JobPost
from .notifications import notify_status_change
from .serializers import (
    ApplicationSerializer, ApplicationStatusSerializer, ApplySerializer, JobSerializer,
)


logger = logging.getLogger(__name__)


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

        # Scoring must never block an application: if it fails we log it and leave the score empty.
        try:
            breakdown = compute_match_breakdown(teacher, job)
        except Exception:
            logger.exception("Match scoring failed for teacher %s / job %s", teacher.pk, job.pk)
            breakdown = None

        try:
            with transaction.atomic():
                app = JobApplication.objects.create(
                    job=job,
                    teacher=teacher,
                    cover_letter=s.validated_data.get("cover_letter", ""),
                    match_score=breakdown["score"] if breakdown else None,
                    match_breakdown=breakdown or {},
                )
                ApplicationAnswer.objects.bulk_create(
                    [ApplicationAnswer(application=app, question=q, answer=answers[q.id]) for q in questions]
                )
                app.attach_documents()  # document auto-fill
        except IntegrityError:  # double-click / two tabs raced past the exists() check
            raise serializers.ValidationError({"detail": "You have already applied to this job."})
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
            "answers__question", "attached_qualifications", "attached_certifications"
        )
        if user.role == "teacher":
            qs = qs.filter(teacher=user.teacher_profile)
        elif user.role == "institute":
            qs = qs.filter(job__institute=user.institute_profile)
        else:
            qs = qs.none()
        if self.request.query_params.get("job"):
            qs = qs.filter(job_id=self.request.query_params["job"])
        # ?ordering=-match_score ranks best matches first (unscored applications go last)
        ordering = self.request.query_params.get("ordering")
        if ordering in ("match_score", "-match_score", "applied_at", "-applied_at"):
            if ordering.lstrip("-") == "match_score":
                f = F("match_score").desc(nulls_last=True) if ordering.startswith("-") else F("match_score").asc(nulls_last=True)
                qs = qs.order_by(f, "-applied_at")
            else:
                qs = qs.order_by(ordering)
        return qs

    def partial_update(self, request, *args, **kwargs):
        app = self.get_object()
        old_status = app.status
        s = ApplicationStatusSerializer(app, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        notify_status_change(app, old_status=old_status)
        return Response(ApplicationSerializer(app, context=self.get_serializer_context()).data)


class InstituteAnalyticsView(APIView):
    """GET /api/institute/analytics/: headline numbers for the institute dashboard.

    "Active" jobs are open and not past their deadline: the same rule teachers see in the job feed.
    `applications_by_status` is the *current* status of each application, so "applied" means
    still unreviewed. All statuses are always present (zero-filled) so the UI can render them.
    """

    permission_classes = [IsInstitute]

    def get(self, request):
        inst = request.user.institute_profile
        today = timezone.localdate()
        jobs = JobPost.objects.filter(institute=inst)
        apps = JobApplication.objects.filter(job__institute=inst)

        active_jobs = (
            jobs.filter(status=JobPost.Status.OPEN)
            .filter(Q(application_deadline__isnull=True) | Q(application_deadline__gte=today))
            .count()
        )

        counts = dict(apps.order_by().values_list("status").annotate(n=Count("id")))
        by_status = {value: counts.get(value, 0) for value, _ in JobApplication.Status.choices}

        per_job = [
            {
                "job_id": j.id,
                "title": j.title,
                "status": j.status,
                "applications": j.total,
                "shortlisted": j.shortlisted,
                "hired": j.hired,
            }
            for j in jobs.order_by("-created_at").annotate(
                total=Count("applications"),
                shortlisted=Count("applications", filter=Q(applications__status="shortlisted")),
                hired=Count("applications", filter=Q(applications__status="hired")),
            )
        ]

        return Response(
            {
                "total_jobs": jobs.count(),
                "active_jobs": active_jobs,
                "total_applications": sum(by_status.values()),
                "applications_by_status": by_status,
                "per_job": per_job,
            }
        )
