from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    message = "Only teacher accounts can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "teacher" and hasattr(u, "teacher_profile"))


class IsInstitute(BasePermission):
    message = "Only institute accounts can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "institute" and hasattr(u, "institute_profile"))
