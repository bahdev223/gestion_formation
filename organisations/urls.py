from django.urls import include, path
from django.views.generic import RedirectView

from dashboard.views import dashboard_home

from . import member_views, views

app_name = "organisations"

urlpatterns = [
    path("comptabilit", RedirectView.as_view(url="comptabilite/")),
    path("comptabilit/", RedirectView.as_view(url="comptabilite/")),
    path("dashboard/", dashboard_home),
    path("abonnement/", views.owner_dashboard, name="owner-dashboard"),
    path("parametres-utilisateurs/", member_views.members_settings, name="members"),
    path("parametres-utilisateurs/inviter/", member_views.invite_member, name="member-invite"),
    path("parametres-utilisateurs/<int:member_id>/modifier/", member_views.edit_member, name="member-edit"),
    path("parametres-utilisateurs/invitations/<int:invitation_id>/annuler/", member_views.cancel_invitation, name="invitation-cancel"),
    path("formations/", include(("formations.urls", "formations"), namespace="formations")),
    path("participants/", include(("participants.urls", "participants"), namespace="participants")),
    path("inscriptions/", include(("inscriptions.urls", "inscriptions"), namespace="inscriptions")),
    path("operations/", include(("operations.urls", "operations"), namespace="operations")),
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
