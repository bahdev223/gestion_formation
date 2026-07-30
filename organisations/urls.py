from django.urls import include, path

from . import views

app_name = "organisations"

urlpatterns = [
    path("dashboard/", views.owner_dashboard, name="owner-dashboard"),
    path("formations/", include(("formations.urls", "formations"), namespace="formations")),
    path("participants/", include(("participants.urls", "participants"), namespace="participants")),
    path("inscriptions/", include(("inscriptions.urls", "inscriptions"), namespace="inscriptions")),
    path("paiements/", include(("paiements.urls", "paiements"), namespace="paiements")),
    path("presences/", include(("presences.urls", "presences"), namespace="presences")),
    path("documents/", include(("documents.urls", "documents"), namespace="documents")),
    path("paie-salariale/", include(("django_paie.urls", "django_paie"), namespace="paie")),
    path("comptabilite/", include(("comptabilite_ohada.urls", "comptabilite"), namespace="comptabilite")),
    path("comptes-financiers/", include(("comptes.urls", "comptes"), namespace="comptes")),
    path(
        "api/comptes-financiers/",
        include(("comptes.urls_api", "comptes_api"), namespace="comptes-api"),
    ),
    path("", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
]
