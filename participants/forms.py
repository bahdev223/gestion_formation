from django import forms

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
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )

