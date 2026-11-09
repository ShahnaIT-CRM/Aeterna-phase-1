from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsTeacher

from .models import Course, Enrollment
from .serializers import (
    CompleteLessonSerializer, CourseDetailSerializer, CourseSerializer, EnrollmentSerializer,
)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Published courses for everyone signed in; enrolling is teachers only. Courses are created in /admin."""

    def get_permissions(self):
        if self.action == "enroll":
            return [IsTeacher()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        return CourseDetailSerializer if self.action == "retrieve" else CourseSerializer

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .annotate(lesson_count=Count("lessons", distinct=True), total_minutes=Sum("lessons__duration_minutes"))
            .prefetch_related("lessons")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.role == "teacher":
            enrollments = Enrollment.objects.filter(teacher=user.teacher_profile).prefetch_related("completed_lessons")
            ctx["enrollments"] = {e.course_id: _with_ids(e) for e in enrollments}
        return ctx

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        course = self.get_object()
        if course.lesson_count == 0:
            raise serializers.ValidationError({"detail": "This course has no lessons yet."})
        teacher = request.user.teacher_profile
        try:
            with transaction.atomic():
                enrollment, created = Enrollment.objects.get_or_create(course=course, teacher=teacher)
        except IntegrityError:  # double-click raced past get_or_create
            created = False
        if not created:
            raise serializers.ValidationError({"detail": "You are already enrolled in this course."})
        return Response(EnrollmentSerializer(enrollment).data, status=201)


def _with_ids(enrollment):
    enrollment.completed_ids = [l.id for l in enrollment.completed_lessons.all()]
    return enrollment


class EnrollmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """A teacher's own enrollments ("My learning") and lesson progress."""

    serializer_class = EnrollmentSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return (
            Enrollment.objects.filter(teacher=self.request.user.teacher_profile)
            .select_related("course")
            .prefetch_related("completed_lessons", "course__lessons")
        )

    @action(detail=True, methods=["post"], url_path="complete-lesson")
    def complete_lesson(self, request, pk=None):
        enrollment = self.get_object()
        s = CompleteLessonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lesson = enrollment.course.lessons.filter(pk=s.validated_data["lesson"]).first()
        if not lesson:
            raise serializers.ValidationError({"lesson": "That lesson is not part of this course."})
        enrollment.mark_lesson_complete(lesson)
        enrollment = self.get_queryset().get(pk=enrollment.pk)
        return Response(EnrollmentSerializer(enrollment).data)
