from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import health_check
from organisations.platform_views import create_organisation, landing_page

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("", landing_page, name="platform-landing"),
    path("creer-entreprise/", create_organisation, name="platform-create-organisation"),
    path("admin/", admin.site.urls),
    path(
        "platform/",
        include(("platform_admin.urls", "platform_admin"), namespace="platform_admin"),
    ),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("o/<slug:organisation_slug>/", include(("organisations.urls", "organisations"), namespace="organisations")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
