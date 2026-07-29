from django.contrib import admin

from .models import ConfigurationOrganisation


@admin.register(ConfigurationOrganisation)
class ConfigurationOrganisationAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "devise", "updated_at")
