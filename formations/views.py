from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, ListView

from core.mixins import HtmxModalFormMixin, OrganisationScopedMixin

from .forms import (
    CategorieFormationForm,
    FormationForm,
    SeanceForm,
    SessionFormationForm,
)
from .models import CategorieFormation, Formation, Seance, SessionFormation


class FormationIndexView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "formations.view_formation"
    model = Formation
    template_name = "formations/index.html"
    context_object_name = "formations"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related("categorie").order_by("-created_at")


class FormationCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "formations.add_formation"
    model = Formation
    form_class = FormationForm
    template_name = "formations/form.html"
    tenant_success_view_name = "formations:index"
    success_message = "La formation a été créée avec succès."
    modal_title = "Nouvelle formation"
    modal_eyebrow = "Catalogue"
    submit_label = "Enregistrer la formation"
    full_width_fields = "description objectifs programme image"


class CategorieListView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "formations.view_categorieformation"
    model = CategorieFormation
    template_name = "formations/categorie_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return super().get_queryset().order_by("nom")


class CategorieCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "formations.add_categorieformation"
    model = CategorieFormation
    form_class = CategorieFormationForm
    template_name = "formations/categorie_form.html"
    tenant_success_view_name = "formations:categorie-list"
    success_message = "La catégorie a été enregistrée avec succès."
    modal_title = "Nouvelle catégorie"
    modal_eyebrow = "Catalogue"
    submit_label = "Enregistrer la catégorie"
    full_width_fields = "description"


class SessionListView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "formations.view_sessionformation"
    model = SessionFormation
    template_name = "formations/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related(
            "formation", "formateur"
        ).order_by("-date_debut", "-created_at")


class SessionCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "formations.add_sessionformation"
    model = SessionFormation
    form_class = SessionFormationForm
    template_name = "formations/session_form.html"
    tenant_success_view_name = "formations:session-list"
    success_message = "La session a été créée avec succès."
    modal_title = "Nouvelle session"
    modal_eyebrow = "Planification"
    submit_label = "Enregistrer la session"
    full_width_fields = "notes paiement_requis_attestation"


class SessionDetailView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "formations.view_sessionformation"
    model = SessionFormation
    template_name = "formations/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "formation", "formateur"
        ).prefetch_related(
            "inscriptions__participant"
        )


class SeanceListView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "formations.view_seance"
    model = Seance
    template_name = "formations/seance_list.html"
    context_object_name = "seances"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related(
            "session", "session__formation"
        ).order_by("-date", "-heure_debut")


class SeanceCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "formations.add_seance"
    model = Seance
    form_class = SeanceForm
    template_name = "formations/seance_form.html"
    tenant_success_view_name = "formations:seance-list"
    success_message = "La séance a été créée avec succès."
    modal_title = "Nouvelle séance"
    modal_eyebrow = "Planification"
    submit_label = "Enregistrer la séance"
    full_width_fields = "contenu observations"
