from django import forms

from subscriptions.services import QuotaService

from .models import Participant


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = [
            "prenom",
            "nom",
            "telephone",
            "telephone_secondaire",
            "email",
            "genre",
            "date_naissance",
            "adresse",
            "ville",
            "pays",
            "profession",
            "entreprise",
            "personne_contact",
            "telephone_contact",
            "photo",
            "notes",
            "statut",
        ]
        labels = {
            "prenom": "Prénom",
            "telephone_secondaire": "Téléphone secondaire",
            "date_naissance": "Date de naissance",
            "personne_contact": "Personne à contacter",
            "telephone_contact": "Téléphone du contact",
        }
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "adresse": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )

    def clean(self):
        cleaned_data = super().clean()
        if self.organisation and self.instance._state.adding:
            try:
                QuotaService.require_participant_slot(self.organisation)
            except forms.ValidationError as exc:
                self.add_error(None, exc)
        photo = cleaned_data.get("photo")
        if self.organisation and photo:
            try:
                QuotaService.require_storage(
                    self.organisation,
                    photo.size,
                )
            except forms.ValidationError as exc:
                self.add_error("photo", exc)
        return cleaned_data
