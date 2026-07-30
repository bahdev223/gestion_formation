from django.urls import path

from . import views

app_name = "platform_admin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organisations/", views.organisation_list, name="organisation-list"),
    path(
        "organisations/creer/",
        views.organisation_create,
        name="organisation-create",
    ),
    path(
        "organisations/<int:organisation_id>/",
        views.organisation_detail,
        name="organisation-detail",
    ),
    path(
        "organisations/<int:organisation_id>/paiement/",
        views.subscription_manual_payment,
        name="subscription-manual-payment",
    ),
    path(
        "organisations/<int:organisation_id>/action/",
        views.organisation_action,
        name="organisation-action",
    ),
    path(
        "organisations/<int:organisation_id>/impersonate/",
        views.impersonate_organisation,
        name="organisation-impersonate",
    ),
    path(
        "organisations/<int:organisation_id>/export/",
        views.export_organisation,
        name="organisation-export",
    ),
    path(
        "impersonation/stop/",
        views.stop_impersonation,
        name="stop-impersonation",
    ),
    path("abonnements/", views.subscriptions_view, name="subscriptions"),
    path("facturation/", views.billing_view, name="billing"),
    path("support/", views.support_list, name="support-list"),
    path(
        "support/<int:ticket_id>/",
        views.support_detail,
        name="support-detail",
    ),
    path("audit/", views.audit_view, name="audit"),
    path("monitoring/", views.monitoring_view, name="monitoring"),
    path("fonctionnalites/", views.feature_flags_view, name="feature-flags"),
    path("maintenance/", views.maintenance_view, name="maintenance"),
    path("sauvegardes/", views.backups_view, name="backups"),
    path("statistiques/", views.analytics_view, name="analytics"),
    path("parametres/", views.settings_view, name="settings"),
]
