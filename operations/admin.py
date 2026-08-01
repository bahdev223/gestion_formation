from django.contrib import admin

from .models import Operation


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("numero", "date_operation", "type_operation", "montant", "statut", "organisation")
    list_filter = ("statut", "type_operation", "organisation")
    search_fields = ("numero", "description")
    date_hierarchy = "date_operation"
