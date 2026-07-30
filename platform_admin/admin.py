from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Announcement,
    BackgroundJob,
    BackupRecord,
    Coupon,
    FeatureFlag,
    MaintenanceWindow,
    PlatformAuditEvent,
    PlatformStaffProfile,
    SaaSInvoice,
    SupportTicket,
    SystemMetric,
    TicketMessage,
)


class TicketMessageInline(TabularInline):
    model = TicketMessage
    extra = 0


@admin.register(PlatformStaffProfile)
class PlatformStaffProfileAdmin(ModelAdmin):
    list_display = ("user", "role", "is_active", "mfa_required", "updated_at")
    list_filter = ("role", "is_active", "mfa_required")
    search_fields = ("user__username", "user__email")


@admin.register(SupportTicket)
class SupportTicketAdmin(ModelAdmin):
    list_display = (
        "numero",
        "titre",
        "organisation",
        "priorite",
        "statut",
        "responsable",
        "created_at",
    )
    list_filter = ("priorite", "statut", "organisation")
    search_fields = ("numero", "titre", "description", "organisation__nom")
    inlines = [TicketMessageInline]


@admin.register(PlatformAuditEvent)
class PlatformAuditEventAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "type_evenement",
        "severite",
        "organisation",
        "acteur",
        "adresse_ip",
    )
    list_filter = ("type_evenement", "severite", "organisation")
    search_fields = ("description", "acteur__username", "adresse_ip")
    readonly_fields = (
        "organisation",
        "acteur",
        "type_evenement",
        "severite",
        "description",
        "adresse_ip",
        "objet_type",
        "objet_id",
        "metadata",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(FeatureFlag)
class FeatureFlagAdmin(ModelAdmin):
    list_display = (
        "code",
        "nom",
        "is_enabled_globally",
        "rollout_percentage",
        "updated_at",
    )
    list_filter = ("is_enabled_globally",)
    search_fields = ("code", "nom", "description")
    filter_horizontal = ("organisations",)


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(ModelAdmin):
    list_display = (
        "titre",
        "starts_at",
        "ends_at",
        "statut",
        "bloque_inscriptions",
        "affiche_banniere",
    )
    list_filter = ("statut", "bloque_inscriptions", "affiche_banniere")


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    list_display = (
        "titre",
        "audience",
        "niveau",
        "is_active",
        "starts_at",
        "ends_at",
    )
    list_filter = ("audience", "niveau", "is_active")


@admin.register(BackupRecord)
class BackupRecordAdmin(ModelAdmin):
    list_display = (
        "organisation",
        "statut",
        "taille_octets",
        "started_at",
        "completed_at",
        "lancee_par",
    )
    list_filter = ("statut", "organisation")


@admin.register(BackgroundJob)
class BackgroundJobAdmin(ModelAdmin):
    list_display = (
        "nom",
        "queue",
        "statut",
        "progression",
        "created_at",
        "completed_at",
    )
    list_filter = ("queue", "statut")


@admin.register(SaaSInvoice)
class SaaSInvoiceAdmin(ModelAdmin):
    list_display = (
        "numero",
        "organisation",
        "montant_ttc",
        "date_emission",
        "date_echeance",
        "statut",
    )
    list_filter = ("statut", "organisation")
    search_fields = ("numero", "organisation__nom")


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = (
        "code",
        "remise_pourcentage",
        "remise_montant",
        "utilisations",
        "is_active",
        "ends_at",
    )
    list_filter = ("is_active",)


@admin.register(SystemMetric)
class SystemMetricAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "cpu_percent",
        "ram_percent",
        "disk_percent",
        "database_ok",
        "errors_500",
        "queue_depth",
    )
    readonly_fields = (
        "cpu_percent",
        "ram_percent",
        "disk_percent",
        "database_latency_ms",
        "response_time_ms",
        "errors_500",
        "queue_depth",
        "database_ok",
        "redis_ok",
        "workers_ok",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
