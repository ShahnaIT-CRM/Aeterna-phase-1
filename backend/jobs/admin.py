from django.contrib import admin

from .models import JobApplication, JobPost, JobQuestion


class QuestionInline(admin.TabularInline):
    model = JobQuestion
    extra = 0


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ["title", "institute", "city", "status", "created_at"]
    list_filter = ["status", "employment_type", "work_mode"]
    search_fields = ["title", "institute__name"]
    inlines = [QuestionInline]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["job", "teacher", "status", "match_score", "applied_at"]
    list_filter = ["status"]
