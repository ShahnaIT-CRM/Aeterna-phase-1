from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from accounts.views import public_profile_shell

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("jobs.urls")),
    path("api/lms/", include("lms.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    # Public prestige profile: same React app, but with link-preview (Open Graph) tags filled in
    re_path(r"^t/(?P<teacher_id>\d+)/?$", public_profile_shell),
    # Everything else is the React single-page app
    re_path(
        r"^(?!api/|admin/|static/|media/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
