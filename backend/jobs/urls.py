from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("jobs", views.JobViewSet, basename="job")
router.register("applications", views.ApplicationViewSet, basename="application")

urlpatterns = [
    path("institute/analytics/", views.InstituteAnalyticsView.as_view()),
] + router.urls
