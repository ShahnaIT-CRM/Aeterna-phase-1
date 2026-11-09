from django.db import models
from django.utils import timezone

from accounts.models import TeacherProfile


class Course(models.Model):
    """A micro-course (1-2 hours of short lessons). Staff create these in the Django admin."""

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=12, choices=Level.choices, default=Level.BEGINNER)
    # Name of the digital badge a teacher earns on completion, e.g. "Flipped Classroom".
    badge_name = models.CharField(max_length=100, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def badge(self):
        return self.badge_name or self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=1)
    duration_minutes = models.PositiveSmallIntegerField(default=10)
    content = models.TextField(blank=True)  # plain text / markdown-ish; rendered as text
    video_url = models.URLField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["course", "order"], name="unique_lesson_order_per_course")]

    def __str__(self):
        return f"{self.course.title} · {self.order}. {self.title}"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = "enrolled", "In progress"
        COMPLETED = "completed", "Completed"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ENROLLED)
    completed_lessons = models.ManyToManyField(Lesson, blank=True, related_name="completed_by")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [models.UniqueConstraint(fields=["course", "teacher"], name="one_enrollment_per_course")]

    def __str__(self):
        return f"{self.teacher} → {self.course}"

    def mark_lesson_complete(self, lesson):
        """Record a finished lesson; flips the enrollment to completed once every lesson is done."""
        self.completed_lessons.add(lesson)
        if self.status != self.Status.COMPLETED:
            total = self.course.lessons.count()
            if total and self.completed_lessons.filter(course=self.course).count() >= total:
                self.status = self.Status.COMPLETED
                self.completed_at = timezone.now()
                self.save(update_fields=["status", "completed_at"])
