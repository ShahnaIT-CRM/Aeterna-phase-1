from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("courses", views.CourseViewSet, basename="course")
router.register("enrollments", views.EnrollmentViewSet, basename="enrollment")

urlpatterns = router.urls
