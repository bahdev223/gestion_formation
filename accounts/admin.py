from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class BalyUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "BALY'S GROUP",
            {
                "fields": (
                    "role",
                    "telephone",
                    "photo",
                    "salaire_mensuel",
                    "must_change_password",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "BALY'S GROUP",
            {
                "fields": (
                    "role",
                    "telephone",
                    "salaire_mensuel",
                )
            },
        ),
    )
