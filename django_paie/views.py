from datetime import date

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView

from documents.services.pdf_service import render_pdf
from organisations.utils import get_request_organisation, tenant_reverse

from .conf import paie_settings
from .models import EcheanceSalariale, PaiementSalarial
from .services import ModeSimpleService, StatistiquesPaieService


class EnterpriseFilterMixin:
    def get_entreprise_id(self):
        organisation = get_request_organisation(self.request)
        if organisation is not None:
            return organisation.slug
        if paie_settings.MODE_PAR_ENTREPRISE:
            entreprise_id = getattr(self.request.user, "entreprise_id", "")
            if not entreprise_id:
                raise PermissionDenied(
                    "Aucune entreprise associée à cet utilisateur."
                )
            return str(entreprise_id)
        return ""

    def get_queryset(self):
        qs = super().get_queryset()
        entreprise_id = self.get_entreprise_id()
        if entreprise_id:
            model = getattr(self, "model", None)
            if model and model is PaiementSalarial:
                qs = qs.filter(echeance__entreprise_id=entreprise_id)
            elif entreprise_id:
                qs = qs.filter(entreprise_id=entreprise_id)
        return qs


class EcheanceListView(PermissionRequiredMixin, EnterpriseFilterMixin, ListView):
    model = EcheanceSalariale
    template_name = "django_paie/echeance_list.html"
    context_object_name = "echeances"
    paginate_by = 50
    permission_required = "django_paie.view_echeancesalariale"

    def get_queryset(self):
        qs = super().get_queryset()
        if statut := self.request.GET.get("statut"):
            qs = qs.filter(statut=statut)
        if periode := self.request.GET.get("periode"):
            try:
                mois, annee = periode.split("/")
                qs = qs.filter(mois=int(mois), annee=int(annee))
            except (ValueError, AttributeError):
                pass
        return qs.select_related("employe_content_type").order_by(
            "-annee", "-mois", "employe_object_id"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statut_choices"] = EcheanceSalariale.STATUT_CHOICES
        return ctx


class EcheanceDetailView(PermissionRequiredMixin, EnterpriseFilterMixin, DetailView):
    model = EcheanceSalariale
    template_name = "django_paie/echeance_detail.html"
    context_object_name = "echeance"
    permission_required = "django_paie.view_echeancesalariale"


class PaiementListView(PermissionRequiredMixin, EnterpriseFilterMixin, ListView):
    model = PaiementSalarial
    template_name = "django_paie/paiement_list.html"
    context_object_name = "paiements"
    paginate_by = 50
    permission_required = "django_paie.view_paiementsalarial"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("echeance")


class PaiementForm(forms.Form):
    echeance = forms.ModelChoiceField(
        queryset=EcheanceSalariale.objects.none(),
        label="Échéance",
    )

    def __init__(self, *args, **kwargs):
        entreprise_id = kwargs.pop("entreprise_id", "")
        super().__init__(*args, **kwargs)
        qs = EcheanceSalariale.objects.all()
        if entreprise_id:
            qs = qs.filter(entreprise_id=entreprise_id)
        self.fields["echeance"].queryset = qs
    montant = forms.DecimalField(label="Montant", min_value=1, max_digits=14, decimal_places=0)
    type_paiement = forms.ChoiceField(
        choices=[("", "Détection automatique")] + list(PaiementSalarial.TYPE_CHOICES),
        label="Type", required=False,
    )
    date_paiement = forms.DateField(
        label="Date de paiement",
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    notes = forms.CharField(label="Notes", required=False, widget=forms.Textarea)


class PaiementCreateView(PermissionRequiredMixin, EnterpriseFilterMixin, FormView):
    template_name = "django_paie/paiement_form.html"
    form_class = PaiementForm
    permission_required = "django_paie.add_paiementsalarial"

    def get_success_url(self):
        return tenant_reverse(self.request, "django_paie:paiement-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["entreprise_id"] = self.get_entreprise_id()
        return kwargs

    def form_valid(self, form):
        entreprise_id = self.get_entreprise_id()
        service = ModeSimpleService(entreprise_id=entreprise_id)
        paiement = service.enregistrer_paiement(
            echeance_id=form.cleaned_data["echeance"].id,
            montant=form.cleaned_data["montant"],
            date_paiement=form.cleaned_data["date_paiement"],
            type_paiement=form.cleaned_data.get("type_paiement") or "PAIEMENT",
            notes=form.cleaned_data.get("notes", ""),
        )
        return redirect(
            tenant_reverse(
                self.request,
                "django_paie:paiement-bulletin",
                kwargs={"pk": paiement.pk},
            )
        )


class DashboardView(PermissionRequiredMixin, EnterpriseFilterMixin, TemplateView):
    template_name = "django_paie/dashboard.html"
    permission_required = "django_paie.view_echeancesalariale"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        entreprise_id = self.get_entreprise_id()

        stats = StatistiquesPaieService(entreprise_id=entreprise_id)
        annee = self.request.GET.get("annee") or None
        if annee:
            try:
                annee = int(annee)
            except ValueError:
                annee = None

        ctx["resume"] = stats.resume_annuel(annee=annee)
        ctx["evolution"] = stats.evolution_mensuelle(annee=annee)
        ctx["arrieres"] = stats.arrieres()
        ctx["avances"] = stats.avances()
        ctx["alertes"] = stats.alertes()
        ctx["annee_selectionnee"] = annee or date.today().year
        ctx["periode_courante_input"] = date.today().strftime("%Y-%m")

        paiements_qs = PaiementSalarial.objects.select_related("echeance")
        if entreprise_id:
            paiements_qs = paiements_qs.filter(echeance__entreprise_id=entreprise_id)
        ctx["derniers_paiements"] = paiements_qs.order_by("-date_paiement")[:10]

        mode = paie_settings.get_mode(entreprise_id)
        ctx["mode"] = mode
        if mode == "COMPLET":
            periode_courante = f"{date.today().month:02d}/{date.today().year}"
            ctx["masse_salariale"] = stats.masse_salariale(periode_courante)
            ctx["cout_employeur"] = stats.cout_employeur(periode_courante)

        return ctx


@login_required
@permission_required("django_paie.view_paiementsalarial", raise_exception=True)
def paiement_bulletin_pdf(request, pk, **kwargs):
    organisation = get_request_organisation(request)
    entreprise_id = organisation.slug if organisation is not None else ""
    paiement = get_object_or_404(
        PaiementSalarial.objects.select_related(
            "echeance",
            "echeance__employe_content_type",
        ),
        pk=pk,
    )
    if entreprise_id:
        if paiement.echeance.entreprise_id != entreprise_id:
            raise PermissionDenied("Paiement introuvable pour cette entreprise.")
    elif paie_settings.MODE_PAR_ENTREPRISE:
        entreprise_id = getattr(request.user, "entreprise_id", "")
        if not entreprise_id:
            raise PermissionDenied("Aucune entreprise associee a cet utilisateur.")
        if paiement.echeance.entreprise_id != str(entreprise_id):
            raise PermissionDenied("Paiement introuvable pour cette entreprise.")

    echeance = paiement.echeance
    bulletins = getattr(echeance, "bulletin_detail", None)
    paiements = echeance.paiements.order_by("date_paiement", "created_at")
    total_retenues = (
        bulletins.total_retenues
        if bulletins
        else max(echeance.montant_brut - echeance.montant_net, 0)
    )
    payload = render_pdf(
        "django_paie/pdf/bulletin.html",
        {
            "paiement": paiement,
            "echeance": echeance,
            "bulletin": bulletins,
            "paiements": paiements,
            "employe": echeance.employe,
            "total_retenues": total_retenues,
        },
    )
    filename = f"bulletin-paie-{echeance.periode.replace('/', '-')}-{paiement.pk}.pdf"
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
