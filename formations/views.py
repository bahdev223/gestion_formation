from datetime import datetime, time

import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError, models
from django.forms import HiddenInput
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import HtmxModalFormMixin, OrganisationScopedMixin
from organisations.utils import tenant_reverse

from .forms import (
    CategorieFormationForm,
    FormationForm,
    SeanceForm,
    SessionFormationForm,
)
from .models import CategorieFormation, Formation, Seance, SessionAccessLink, SessionFormation


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


class FormationUpdateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "formations.change_formation"
    model = Formation
    form_class = FormationForm
    template_name = "formations/form.html"
    tenant_success_view_name = "formations:index"
    success_message = "La formation a Ã©tÃ© modifiÃ©e avec succÃ¨s."
    modal_title = "Modifier la formation"
    modal_eyebrow = "Catalogue"
    submit_label = "Enregistrer les changements"
    full_width_fields = "description objectifs programme image"


class FormationDeleteView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "formations.delete_formation"
    model = Formation
    template_name = "formations/delete_confirm.html"
    tenant_success_view_name = "formations:index"

    def get_success_url(self):
        from organisations.utils import tenant_reverse

        return tenant_reverse(self.request, self.tenant_success_view_name)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("organisation", None)
        return kwargs

    def form_valid(self, form):
        return DeleteView.form_valid(self, form)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.sessions.exists():
            messages.error(
                request,
                (
                    "Suppression impossible : cette formation est liÃ©e Ã  "
                    f"{self.object.sessions.count()} session(s). "
                    "Supprimez ou dÃ©placez ces sessions avant de continuer."
                ),
            )
            return redirect(self.get_success_url())
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(
                request,
                f"La formation Â« {self.object.nom} Â» a Ã©tÃ© supprimÃ©e avec succÃ¨s.",
            )
            return response
        except IntegrityError:
            messages.error(
                request,
                "Suppression impossible : la formation est rÃ©fÃ©rencÃ©e par d'autres donnÃ©es.",
            )
            return redirect(self.get_success_url())


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
        queryset = super().get_queryset().select_related(
            "formation", "formateur"
        ).annotate(
            inscriptions_count=models.Count("inscriptions", distinct=True),
            seances_count=models.Count("seances", distinct=True),
        )
        search = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(titre__icontains=search)
                | models.Q(formation__nom__icontains=search)
                | models.Q(formateur__username__icontains=search)
                | models.Q(formateur__first_name__icontains=search)
                | models.Q(formateur__last_name__icontains=search)
                | models.Q(lieu__icontains=search)
            )
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset.order_by("-date_debut", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_queryset()
        context.update(
            {
                "search_query": self.request.GET.get("q", "").strip(),
                "active_statut": self.request.GET.get("statut", "").strip(),
                "statut_choices": SessionFormation.Statut.choices,
                "sessions_total": base_qs.count(),
                "sessions_actives": base_qs.filter(
                    statut__in=[
                        SessionFormation.Statut.PLANIFIEE,
                        SessionFormation.Statut.INSCRIPTIONS_OUVERTES,
                        SessionFormation.Statut.EN_COURS,
                    ]
                ).count(),
                "sessions_apprenants": sum(
                    session.inscriptions_count for session in base_qs
                ),
                "sessions_seances": sum(
                    session.seances_count for session in base_qs
                ),
            }
        )
        return context


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
            models.Prefetch(
                "seances",
                queryset=Seance.objects.order_by("date", "heure_debut"),
            ),
            "inscriptions__participant",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            access_link = self.object.public_access
        except SessionAccessLink.DoesNotExist:
            access_link = None
        public_session_url = ""
        public_qr_url = ""
        if access_link:
            public_session_url = self.request.build_absolute_uri(
                tenant_reverse(
                    self.request,
                    "formations:session-public",
                    kwargs={"token": access_link.token},
                )
            )
            public_qr_url = tenant_reverse(
                self.request,
                "formations:session-public-qr",
                kwargs={"token": access_link.token},
            )
        context.update(
            {
                "session_access_link": access_link,
                "public_session_url": public_session_url,
                "public_qr_url": public_qr_url,
            }
        )
        return context


def _session_public_expires_at(session):
    end_of_day = datetime.combine(session.date_fin, time.max)
    if timezone.is_naive(end_of_day):
        return timezone.make_aware(end_of_day)
    return end_of_day


def _session_detail_url(request, session):
    return tenant_reverse(
        request,
        "formations:session-detail",
        kwargs={"pk": session.pk},
    )


@login_required
@permission_required("formations.change_sessionformation", raise_exception=True)
def session_access_action(request, pk, action, organisation_slug=None):
    session = get_object_or_404(
        SessionFormation,
        pk=pk,
        organisation=request.organisation,
    )
    if request.method != "POST":
        messages.warning(request, "Utilisez le bouton de la session pour modifier le lien apprenants.")
        return redirect(_session_detail_url(request, session))
    try:
        access_link = session.public_access
    except SessionAccessLink.DoesNotExist:
        access_link = None
    if action == "enable":
        access_link, _ = SessionAccessLink.objects.get_or_create(
            session=session,
            defaults={
                "organisation": session.organisation,
                "expires_at": _session_public_expires_at(session),
            },
        )
        access_link.is_active = True
        access_link.expires_at = _session_public_expires_at(session)
        access_link.save(update_fields=["is_active", "expires_at", "updated_at"])
        messages.success(request, "Le lien apprenants est actif.")
    elif action == "disable":
        if access_link:
            access_link.is_active = False
            access_link.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Le lien apprenants a ete desactive.")
    elif action == "regenerate":
        if access_link is None:
            access_link = SessionAccessLink.objects.create(
                session=session,
                organisation=session.organisation,
                expires_at=_session_public_expires_at(session),
            )
        else:
            access_link.expires_at = _session_public_expires_at(session)
            access_link.regenerate()
        messages.success(request, "Un nouveau lien apprenants a ete genere.")
    else:
        raise Http404("Action inconnue.")
    return redirect(_session_detail_url(request, session))


class SessionPublicAccessView(DetailView):
    model = SessionAccessLink
    template_name = "formations/session_public.html"
    context_object_name = "access_link"
    slug_field = "token"
    slug_url_kwarg = "token"

    def get_queryset(self):
        return SessionAccessLink.objects.select_related(
            "organisation",
            "session",
            "session__formation",
            "session__formateur",
        ).prefetch_related(
            models.Prefetch(
                "session__seances",
                queryset=Seance.objects.exclude(
                    statut=Seance.Statut.ANNULEE,
                ).order_by("date", "heure_debut"),
            )
        ).filter(organisation=self.request.organisation)

    def get_object(self, queryset=None):
        access_link = super().get_object(queryset)
        if not access_link.is_valid:
            raise Http404("Lien apprenants indisponible.")
        return access_link

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session"] = self.object.session
        context["organisation"] = self.object.organisation
        context["qr_url"] = tenant_reverse(
            self.request,
            "formations:session-public-qr",
            kwargs={"token": self.object.token},
        )
        return context


def session_public_qr(request, token, organisation_slug=None):
    access_link = get_object_or_404(
        SessionAccessLink.objects.select_related("organisation"),
        token=token,
        organisation=request.organisation,
    )
    if not access_link.is_valid:
        raise Http404("Lien apprenants indisponible.")
    url = request.build_absolute_uri(
        tenant_reverse(
            request,
            "formations:session-public",
            kwargs={"token": access_link.token},
        )
    )
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    return HttpResponse(image.to_string(), content_type="image/svg+xml")


class SeanceCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "formations.add_seance"
    model = Seance
    form_class = SeanceForm
    template_name = "formations/seance_form.html"
    tenant_success_view_name = "formations:session-list"
    success_message = "La séance a été créée avec succès."
    modal_title = "Nouvelle séance"
    modal_eyebrow = "Planification"
    submit_label = "Enregistrer la séance"
    full_width_fields = "contenu observations"

    def _selected_session(self):
        session_id = self.request.GET.get("session") or self.request.POST.get("session")
        if not session_id:
            return None
        try:
            return SessionFormation.objects.get(
                pk=int(session_id),
                organisation=self.get_current_organisation(),
            )
        except (SessionFormation.DoesNotExist, TypeError, ValueError):
            return None

    def get_initial(self):
        initial = super().get_initial()
        session = self._selected_session()
        if session is not None:
            initial["session"] = session.pk
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        session = self._selected_session()
        if session is not None:
            form.fields["session"].widget = HiddenInput()
            form.fields["session"].queryset = SessionFormation.objects.filter(pk=session.pk)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self._selected_session()
        from organisations.utils import tenant_reverse

        if session is not None:
            context["cancel_url"] = tenant_reverse(
                self.request, "formations:session-detail", kwargs={"pk": session.pk}
            )
        else:
            context["cancel_url"] = tenant_reverse(
                self.request, "formations:session-list"
            )
        return context

    def get_success_url(self):
        session = self._selected_session()
        if session is not None:
            from organisations.utils import tenant_reverse

            return tenant_reverse(
                self.request,
                "formations:session-detail",
                kwargs={"pk": session.pk},
            )
        return super().get_success_url()
