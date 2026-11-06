from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("jobs.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    # Everything else is the React single-page app
    re_path(
        r"^(?!api/|admin/|static/|media/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
