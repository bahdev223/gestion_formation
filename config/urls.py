from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard.payroll_views import payroll_payment_create

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include(("accounts.urls", "accounts"), namespace="comptes-utilisateurs")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("formations/", include(("formations.urls", "formations"), namespace="formations")),
    path("participants/", include(("participants.urls", "participants"), namespace="participants")),
    path("inscriptions/", include(("inscriptions.urls", "inscriptions"), namespace="inscriptions")),
    path("paiements/", include(("paiements.urls", "paiements"), namespace="paiements")),
    path("presences/", include(("presences.urls", "presences"), namespace="presences")),
    path("documents/", include(("documents.urls", "documents"), namespace="documents")),
    path("paie-salariale/paiements/creer/", payroll_payment_create),
    path("paie-salariale/", include("django_paie.urls")),
    path("ressources-humaines/", include("django_rh.urls")),
    path("comptes-financiers/", include("comptes.urls")),
    path("api/comptes-financiers/", include("comptes.urls_api")),
    path("comptabilite/", include("comptabilite_ohada.urls")),
    path("", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
