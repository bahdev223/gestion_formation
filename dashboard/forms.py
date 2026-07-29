from django import forms

from .models import ConfigurationOrganisation


class ConfigurationOrganisationForm(forms.ModelForm):
    class Meta:
        model = ConfigurationOrganisation
        fields = [
            "nom",
            "logo",
            "adresse",
            "telephone",
            "email",
            "site_web",
            "numero_fiscal",
            "devise",
            "prefixe_recu",
            "prefixe_attestation",
            "signature_nom",
            "signature_fonction",
            "signature_image",
            "cachet_image",
        ]
        labels = {
            "nom": "Nom de l’entreprise",
            "logo": "Logo de l’entreprise",
            "site_web": "Site web",
            "numero_fiscal": "Numéro fiscal / RCCM",
            "devise": "Devise",
            "prefixe_recu": "Préfixe des reçus",
            "prefixe_attestation": "Préfixe des attestations",
            "signature_nom": "Nom du signataire",
            "signature_fonction": "Fonction du signataire",
            "signature_image": "Signature",
            "cachet_image": "Cachet de l’entreprise",
        }
        widgets = {
            "adresse": forms.Textarea(attrs={"rows": 3}),
            "email": forms.EmailInput(attrs={"placeholder": "contact@entreprise.com"}),
            "site_web": forms.URLInput(attrs={"placeholder": "https://"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full border border-slate-300 bg-white px-3.5 py-3 text-sm "
                "text-slate-900 outline-none transition focus:border-blue-600 "
                "focus:ring-2 focus:ring-blue-100"
            )

