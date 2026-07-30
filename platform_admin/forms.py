from django import forms

from .models import (
    Announcement,
    FeatureFlag,
    MaintenanceWindow,
    SupportTicket,
)

FIELD_CLASS = (
    "w-full border border-slate-300 bg-white px-3 py-2.5 text-sm "
    "text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 "
    "focus:ring-cyan-100"
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = FIELD_CLASS


class SupportTicketUpdateForm(StyledModelForm):
    class Meta:
        model = SupportTicket
        fields = ["priorite", "statut", "responsable"]


class FeatureFlagForm(StyledModelForm):
    class Meta:
        model = FeatureFlag
        fields = [
            "code",
            "nom",
            "description",
            "is_enabled_globally",
            "rollout_percentage",
            "organisations",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "organisations": forms.SelectMultiple(attrs={"size": 8}),
        }


class MaintenanceWindowForm(StyledModelForm):
    class Meta:
        model = MaintenanceWindow
        fields = [
            "titre",
            "message",
            "starts_at",
            "ends_at",
            "statut",
            "bloque_inscriptions",
            "affiche_banniere",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class AnnouncementForm(StyledModelForm):
    class Meta:
        model = Announcement
        fields = [
            "titre",
            "message",
            "audience",
            "niveau",
            "is_active",
            "starts_at",
            "ends_at",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
