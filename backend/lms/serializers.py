from rest_framework import serializers

from .models import Course, Enrollment, Lesson


class LessonOutlineSerializer(serializers.ModelSerializer):
    """Title and length only: what anyone can see before enrolling."""

    class Meta:
        model = Lesson
        fields = ["id", "order", "title", "duration_minutes"]


class LessonFullSerializer(LessonOutlineSerializer):
    completed = serializers.SerializerMethodField()

    class Meta(LessonOutlineSerializer.Meta):
        fields = LessonOutlineSerializer.Meta.fields + ["content", "video_url", "completed"]

    def get_completed(self, obj):
        return obj.id in self.context.get("completed_ids", ())


def _progress(done, total):
    return round(100 * done / total) if total else 0


class CourseSerializer(serializers.ModelSerializer):
    """List card. `lesson_count` / `total_minutes` come from the viewset's annotations; the
    teacher's own enrollment (if any) comes from `context["enrollments"]`, keyed by course id."""

    badge = serializers.CharField(read_only=True)
    lesson_count = serializers.IntegerField(read_only=True)
    total_minutes = serializers.SerializerMethodField()
    enrollment_id = serializers.SerializerMethodField()
    enrollment_status = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "title", "summary", "level", "badge", "lesson_count", "total_minutes",
            "enrollment_id", "enrollment_status", "progress",
        ]

    def _enrollment(self, obj):
        return self.context.get("enrollments", {}).get(obj.id)

    def get_total_minutes(self, obj):
        return getattr(obj, "total_minutes", None) or 0

    def get_enrollment_id(self, obj):
        e = self._enrollment(obj)
        return e.id if e else None

    def get_enrollment_status(self, obj):
        e = self._enrollment(obj)
        return e.status if e else None

    def get_progress(self, obj):
        e = self._enrollment(obj)
        if not e:
            return 0
        return _progress(len(e.completed_ids), getattr(obj, "lesson_count", 0))


class CourseDetailSerializer(CourseSerializer):
    description = serializers.CharField(read_only=True)
    lessons = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ["description", "lessons"]

    def get_lessons(self, obj):
        """Lesson content and videos are only sent to teachers who are enrolled."""
        e = self._enrollment(obj)
        lessons = obj.lessons.all()
        if not e:
            return LessonOutlineSerializer(lessons, many=True).data
        ctx = {**self.context, "completed_ids": set(e.completed_ids)}
        return LessonFullSerializer(lessons, many=True, context=ctx).data


class EnrollmentSerializer(serializers.ModelSerializer):
    course = serializers.SerializerMethodField()
    badge = serializers.CharField(source="course.badge", read_only=True)
    completed_lesson_ids = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id", "course", "status", "badge", "progress", "completed_lesson_ids",
            "enrolled_at", "completed_at",
        ]

    def get_course(self, obj):
        return {"id": obj.course_id, "title": obj.course.title, "level": obj.course.level}

    def get_completed_lesson_ids(self, obj):
        return [l.id for l in obj.completed_lessons.all()]

    def get_progress(self, obj):
        return _progress(len(self.get_completed_lesson_ids(obj)), obj.course.lessons.count())


class CompleteLessonSerializer(serializers.Serializer):
    lesson = serializers.IntegerField()
