from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import InvitationOrganisation, MembreOrganisation, Organisation


class MembreOrganisationInline(TabularInline):
    model = MembreOrganisation
    extra = 0
    autocomplete_fields = ["user", "invited_by"]
    fields = ["user", "role", "is_active", "invited_by"]


@admin.register(Organisation)
class OrganisationAdmin(ModelAdmin):
    list_display = ("nom", "slug", "email", "telephone", "statut", "is_active", "created_at")
    list_filter = ("statut", "is_active", "pays")
    search_fields = ("nom", "slug", "email", "telephone")
    prepopulated_fields = {"slug": ("nom",)}
    inlines = [MembreOrganisationInline]
    actions = ["activer_organisations", "suspendre_organisations"]

    @admin.action(description="Activer les organisations sélectionnées")
    def activer_organisations(self, request, queryset):
        queryset.update(statut=Organisation.Statut.ACTIVE, is_active=True)

    @admin.action(description="Suspendre les organisations sélectionnées")
    def suspendre_organisations(self, request, queryset):
        queryset.update(statut=Organisation.Statut.SUSPENDUE, is_active=False)


@admin.register(MembreOrganisation)
class MembreOrganisationAdmin(ModelAdmin):
    list_display = ("organisation", "user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("organisation__nom", "user__username", "user__email")
    autocomplete_fields = ["organisation", "user", "invited_by"]


@admin.register(InvitationOrganisation)
class InvitationOrganisationAdmin(ModelAdmin):
    list_display = ("email", "organisation", "role", "statut", "expire_le", "invited_by")
    list_filter = ("statut", "role")
    search_fields = ("email", "organisation__nom")
    readonly_fields = ("token", "accepted_at", "created_at", "updated_at")
    autocomplete_fields = ["organisation", "invited_by", "accepted_by"]
