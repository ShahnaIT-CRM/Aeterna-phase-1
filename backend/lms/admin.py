from django.contrib import admin

from .models import Course, Enrollment, Lesson


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "level", "badge_name", "is_published"]
    list_filter = ["is_published", "level"]
    list_editable = ["is_published"]
    search_fields = ["title"]
    inlines = [LessonInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["teacher", "course", "status", "enrolled_at", "completed_at"]
    list_filter = ["status", "course"]
