from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Certification, EmploymentHistory, InstituteProfile, Qualification, TeacherProfile, User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "is_active", "is_staff"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role", {"fields": ("role", "email_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "role", "password1", "password2")}),)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "city", "employment_status", "total_experience_years"]
    search_fields = ["first_name", "last_name", "user__email"]


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ["teacher", "course", "university", "year_of_passing", "verification_status", "blockchain_tx_hash"]
    list_filter = ["verification_status", "level"]
    list_editable = ["verification_status"]
    readonly_fields = ["blockchain_tx_hash", "document_sha256", "blockchain_block", "verified_at", "verified_by"]


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ["teacher", "name", "issuing_organization", "verification_status"]
    list_filter = ["verification_status"]
    list_editable = ["verification_status"]


admin.site.register(EmploymentHistory)


@admin.register(InstituteProfile)
class InstituteProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "verification_status", "subscription_plan", "job_post_quota"]
    list_filter = ["verification_status", "subscription_plan"]
    list_editable = ["verification_status", "subscription_plan", "job_post_quota"]
    search_fields = ["name", "registration_number"]
