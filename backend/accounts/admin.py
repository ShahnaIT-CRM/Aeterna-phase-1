from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Certification, EmploymentHistory, InstituteProfile, Notification, Qualification, TeacherMeritScore,
    TeacherProfile, UniversityProfile, User,
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
    list_display = ["teacher", "course", "university", "year_of_passing", "verification_status", "signed_at"]
    list_filter = ["verification_status", "level"]
    search_fields = ["teacher__first_name", "teacher__last_name", "university__name"]
    # Signatures can only be made by the university (Issue & Sign), never typed in here.
    readonly_fields = ["document_sha256", "signature", "signed_by", "signed_at", "created_at"]


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


@admin.register(UniversityProfile)
class UniversityProfileAdmin(admin.ModelAdmin):
    """Setting 'verified' here mints the university's Ed25519 key pair (see UniversityProfile.save)."""
    list_display = ["name", "city", "verification_status", "is_trusted_issuer", "nirf_rank", "has_account", "key_fingerprint"]
    list_filter = ["verification_status", "is_trusted_issuer"]
    list_editable = ["verification_status", "is_trusted_issuer", "nirf_rank"]
    search_fields = ["name", "user__email"]
    # The encrypted private key is not shown, not editable and not exported anywhere.
    fields = [
        "user", "name", "city", "state", "website", "logo", "verification_status", "is_trusted_issuer",
        "nirf_rank", "public_key", "keys_generated_at",
    ]
    readonly_fields = ["public_key", "keys_generated_at"]

    @admin.display(boolean=True)
    def has_account(self, obj):
        return obj.user_id is not None


@admin.register(TeacherMeritScore)
class TeacherMeritScoreAdmin(admin.ModelAdmin):
    list_display = ["teacher", "score", "tier", "calculated_at"]
    list_filter = ["tier"]
    readonly_fields = ["teacher", "score", "tier", "headline", "breakdown", "calculated_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "kind", "title", "is_read", "created_at"]
    list_filter = ["kind", "is_read"]
