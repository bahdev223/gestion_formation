from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from .models import Abonnement, PaiementAbonnement, PlanAbonnement


@admin.register(PlanAbonnement)
class PlanAbonnementAdmin(ModelAdmin):
    list_display = (
        "code",
        "nom",
        "prix_mensuel",
        "prix_annuel",
        "max_utilisateurs",
        "max_participants",
        "max_formations_actives",
        "is_active",
        "ordre",
    )
    list_filter = ("code", "is_active")
    search_fields = ("code", "nom")


class PaiementAbonnementInline(TabularInline):
    model = PaiementAbonnement
    extra = 0
    fields = ("reference", "montant", "mode_paiement", "statut", "date_paiement")
    readonly_fields = ("reference",)


@admin.register(Abonnement)
class AbonnementAdmin(ModelAdmin):
    list_display = (
        "organisation",
        "plan",
        "cycle",
        "statut",
        "date_debut",
        "date_fin",
        "montant",
    )
    list_filter = ("statut", "cycle", "plan")
    search_fields = ("organisation__nom", "organisation__slug")
    autocomplete_fields = ["organisation", "plan"]
    inlines = [PaiementAbonnementInline]
    actions = ["activer_abonnements", "suspendre_abonnements", "expirer_abonnements"]

    @admin.action(description="Activer les abonnements sélectionnés")
    def activer_abonnements(self, request, queryset):
        queryset.update(statut=Abonnement.Statut.ACTIF)

    @admin.action(description="Suspendre les abonnements sélectionnés")
    def suspendre_abonnements(self, request, queryset):
        queryset.update(statut=Abonnement.Statut.SUSPENDU)

    @admin.action(description="Marquer comme expirés")
    def expirer_abonnements(self, request, queryset):
        queryset.update(statut=Abonnement.Statut.EXPIRE)


@admin.register(PaiementAbonnement)
class PaiementAbonnementAdmin(ModelAdmin):
    list_display = (
        "reference",
        "abonnement",
        "montant",
        "mode_paiement",
        "statut",
        "date_paiement",
    )
    list_filter = ("statut", "mode_paiement")
    search_fields = ("reference", "abonnement__organisation__nom")
    autocomplete_fields = ["abonnement"]
    actions = ["valider_paiements", "annuler_paiements"]

    @admin.action(description="Valider les paiements sélectionnés")
    def valider_paiements(self, request, queryset):
        for paiement in queryset:
            paiement.statut = PaiementAbonnement.Statut.VALIDE
            paiement.date_paiement = timezone.now()
            paiement.save(
                update_fields=["statut", "date_paiement", "updated_at"]
            )

    @admin.action(description="Annuler les paiements sélectionnés")
    def annuler_paiements(self, request, queryset):
        queryset.update(statut=PaiementAbonnement.Statut.ANNULE)
