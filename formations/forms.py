from django import forms

from subscriptions.services import QuotaService

from .models import CategorieFormation, Formation, Seance, SessionFormation

FIELD_CLASSES = (
    "w-full border border-slate-300 bg-white px-3.5 py-3 text-sm "
    "text-slate-900 outline-none transition focus:border-blue-600 "
    "focus:ring-2 focus:ring-blue-100"
)


def style_form_fields(form):
    for field in form.fields.values():
        field.widget.attrs["class"] = FIELD_CLASSES


class FormationForm(forms.ModelForm):
    nouvelle_categorie = forms.CharField(
        label="Nouvelle catégorie",
        required=False,
        help_text="À renseigner uniquement si la catégorie n'existe pas encore.",
    )

    class Meta:
        model = Formation
        fields = [
            "nom",
            "categorie",
            "nouvelle_categorie",
            "description",
            "objectifs",
            "programme",
            "duree",
            "unite_duree",
            "prix_standard",
            "image",
            "statut",
        ]
        labels = {
            "nom": "Nom de la formation",
            "categorie": "Catégorie existante",
            "duree": "Durée",
            "unite_duree": "Unité",
            "prix_standard": "Prix standard (FCFA)",
            "image": "Image de couverture",
        }
        help_texts = {
            "image": "Formats JPG, PNG ou WebP. Taille maximale : 5 Mo.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "objectifs": forms.Textarea(attrs={"rows": 3}),
            "programme": forms.Textarea(attrs={"rows": 5}),
            "prix_standard": forms.NumberInput(attrs={"min": 0, "step": 500}),
            "duree": forms.NumberInput(attrs={"min": 1}),
            "image": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        self.organisation = organisation
        super().__init__(*args, **kwargs)
        self.fields["categorie"].required = False
        categories = CategorieFormation.objects.filter(
            is_active=True
        )
        if organisation:
            categories = categories.filter(organisation=organisation)
        self.fields["categorie"].queryset = categories.order_by("nom")

        style_form_fields(self)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "L’image de couverture ne doit pas dépasser 5 Mo."
            )
        content_type = getattr(image, "content_type", "")
        if content_type and content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise forms.ValidationError(
                "Utilisez une image JPG, PNG ou WebP."
            )
        return image

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("categorie") and not cleaned_data.get(
            "nouvelle_categorie", ""
        ).strip():
            self.add_error(
                "nouvelle_categorie",
                "Choisissez une catégorie existante ou saisissez-en une nouvelle.",
            )
        becomes_active = (
            cleaned_data.get("statut") == Formation.Statut.ACTIVE
            and (
                self.instance._state.adding
                or self.instance.statut != Formation.Statut.ACTIVE
            )
        )
        if self.organisation and becomes_active:
            try:
                QuotaService.require_active_formation_slot(
                    self.organisation
                )
            except forms.ValidationError as exc:
                self.add_error("statut", exc)
        image = cleaned_data.get("image")
        if self.organisation and image:
            try:
                QuotaService.require_storage(
                    self.organisation,
                    image.size,
                )
            except forms.ValidationError as exc:
                self.add_error("image", exc)
        return cleaned_data

    def save(self, commit=True):
        formation = super().save(commit=False)
        nouvelle_categorie = self.cleaned_data.get("nouvelle_categorie", "").strip()
        if nouvelle_categorie:
            categorie, _ = CategorieFormation.objects.get_or_create(
                organisation=formation.organisation,
                nom=nouvelle_categorie,
            )
            formation.categorie = categorie
        if commit:
            formation.save()
        return formation


class CategorieFormationForm(forms.ModelForm):
    class Meta:
        model = CategorieFormation
        fields = ["nom", "description", "couleur", "is_active"]
        labels = {
            "nom": "Nom de la catégorie",
            "description": "Description",
            "couleur": "Couleur d’identification",
            "is_active": "Catégorie active",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "couleur": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        style_form_fields(self)
        self.fields["is_active"].widget.attrs["class"] = (
            "h-4 w-4 border-slate-300 text-blue-600 focus:ring-blue-500"
        )


class SessionFormationForm(forms.ModelForm):
    class Meta:
        model = SessionFormation
        fields = [
            "formation",
            "titre",
            "formateur",
            "date_debut",
            "date_fin",
            "heure_debut",
            "heure_fin",
            "lieu",
            "capacite_max",
            "prix_applique",
            "seuil_presence_attestation",
            "paiement_requis_attestation",
            "notes",
            "statut",
        ]
        labels = {
            "capacite_max": "Capacité maximale",
            "prix_applique": "Prix appliqué (FCFA)",
            "seuil_presence_attestation": "Présence minimale pour l'attestation (%)",
            "paiement_requis_attestation": "Paiement intégral requis pour l'attestation",
        }
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
            "heure_debut": forms.TimeInput(attrs={"type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "capacite_max": forms.NumberInput(attrs={"min": 1}),
            "prix_applique": forms.NumberInput(attrs={"min": 0, "step": 500}),
            "seuil_presence_attestation": forms.NumberInput(
                attrs={"min": 0, "max": 100, "step": 1}
            ),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        formations = Formation.objects.exclude(
            statut=Formation.Statut.ARCHIVEE
        )
        if organisation:
            formations = formations.filter(organisation=organisation)
        self.fields["formation"].queryset = formations.order_by("nom")
        style_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin", "La date de fin doit être postérieure à la date de début."
            )
        return cleaned_data


class SeanceForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = [
            "session",
            "titre",
            "date",
            "heure_debut",
            "heure_fin",
            "lieu",
            "contenu",
            "observations",
            "statut",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "heure_debut": forms.TimeInput(attrs={"type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"type": "time"}),
            "contenu": forms.Textarea(attrs={"rows": 4}),
            "observations": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        sessions = SessionFormation.objects.select_related(
            "formation"
        ).exclude(statut=SessionFormation.Statut.ANNULEE)
        if organisation:
            sessions = sessions.filter(organisation=organisation)
        self.fields["session"].queryset = sessions.order_by("-date_debut")
        style_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        heure_debut = cleaned_data.get("heure_debut")
        heure_fin = cleaned_data.get("heure_fin")
        if heure_debut and heure_fin and heure_fin <= heure_debut:
            self.add_error(
                "heure_fin", "L'heure de fin doit être postérieure à l'heure de début."
            )
        return cleaned_data
