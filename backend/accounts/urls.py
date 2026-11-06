from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register("teacher/qualifications", views.QualificationViewSet, basename="qualification")
router.register("teacher/certifications", views.CertificationViewSet, basename="certification")
router.register("teacher/employment", views.EmploymentViewSet, basename="employment")

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/login/", TokenObtainPairView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("teacher/profile/", views.TeacherProfileView.as_view()),
    path("institute/profile/", views.InstituteProfileView.as_view()),
    path("", include(router.urls)),
]
