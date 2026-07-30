from django import forms

from .models import ConfigurationOrganisation


class ConfigurationOrganisationForm(forms.ModelForm):
    color_fields = {
        "couleur_sidebar",
        "couleur_header",
        "couleur_primaire",
        "couleur_secondaire",
        "couleur_accent",
        "couleur_fond",
        "couleur_surface",
    }
    css_variable_by_field = {
        "couleur_sidebar": "--baly-blue-deep",
        "couleur_header": "--baly-header",
        "couleur_primaire": "--baly-blue",
        "couleur_secondaire": "--baly-blue-dark",
        "couleur_accent": "--baly-orange",
        "couleur_fond": "--baly-bg",
        "couleur_surface": "--baly-surface",
    }

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
            "palette",
            "couleur_sidebar",
            "couleur_header",
            "couleur_primaire",
            "couleur_secondaire",
            "couleur_accent",
            "couleur_fond",
            "couleur_surface",
        ]
        labels = {
            "nom": "Nom de l'entreprise",
            "logo": "Logo de l'entreprise",
            "site_web": "Site web",
            "numero_fiscal": "Numero fiscal / RCCM",
            "devise": "Devise",
            "prefixe_recu": "Prefixe des recus",
            "prefixe_attestation": "Prefixe des attestations",
            "signature_nom": "Nom du signataire",
            "signature_fonction": "Fonction du signataire",
            "signature_image": "Signature",
            "cachet_image": "Cachet de l'entreprise",
            "palette": "Palette rapide",
            "couleur_sidebar": "Sidebar",
            "couleur_header": "Header",
            "couleur_primaire": "Couleur principale",
            "couleur_secondaire": "Couleur secondaire",
            "couleur_accent": "Couleur d'accent",
            "couleur_fond": "Fond de l'application",
            "couleur_surface": "Surfaces",
        }
        widgets = {
            "adresse": forms.Textarea(attrs={"rows": 3}),
            "email": forms.EmailInput(attrs={"placeholder": "contact@entreprise.com"}),
            "site_web": forms.URLInput(attrs={"placeholder": "https://"}),
            "couleur_sidebar": forms.TextInput(attrs={"type": "color"}),
            "couleur_header": forms.TextInput(attrs={"type": "color"}),
            "couleur_primaire": forms.TextInput(attrs={"type": "color"}),
            "couleur_secondaire": forms.TextInput(attrs={"type": "color"}),
            "couleur_accent": forms.TextInput(attrs={"type": "color"}),
            "couleur_fond": forms.TextInput(attrs={"type": "color"}),
            "couleur_surface": forms.TextInput(attrs={"type": "color"}),
        }
        help_texts = {
            "palette": "Choisissez une base, puis ajustez les couleurs si besoin.",
            "couleur_sidebar": "Couleur de fond du menu lateral.",
            "couleur_header": "Couleur de la barre superieure.",
            "couleur_accent": "Utilisee pour les boutons forts et les elements actifs.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "w-full border border-slate-300 bg-white px-3.5 py-3 text-sm "
                "text-slate-900 outline-none transition focus:border-blue-600 "
                "focus:ring-2 focus:ring-blue-100"
            )
            if name in self.color_fields:
                field.widget.attrs["class"] = (
                    "h-11 w-full cursor-pointer border border-slate-300 bg-white p-1 "
                    "outline-none transition focus:border-blue-600 focus:ring-2 "
                    "focus:ring-blue-100"
                )
                field.widget.attrs["data-css-var"] = self.css_variable_by_field[name]
                field.widget.attrs["x-on:input"] = (
                    "document.documentElement.style.setProperty("
                    "$event.target.dataset.cssVar, $event.target.value)"
                )
