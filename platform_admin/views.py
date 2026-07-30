from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import (
    Abonnement,
    PaiementAbonnement,
    PlanAbonnement,
)
from subscriptions.services import expiring_subscription_alerts

from .access import platform_role_required
from .backup_service import create_tenant_backup
from .forms import (
    AnnouncementForm,
    FeatureFlagForm,
    MaintenanceWindowForm,
    ManualSubscriptionPaymentForm,
    PlatformOrganisationCreateForm,
    SupportTicketUpdateForm,
)
from .models import (
    Announcement,
    BackgroundJob,
    BackupRecord,
    Coupon,
    FeatureFlag,
    MaintenanceWindow,
    PlatformAuditEvent,
    PlatformStaffProfile,
    SaaSInvoice,
    SupportTicket,
    SystemMetric,
    TicketMessage,
)
from .services import (
    analytics_data,
    create_platform_organisation,
    live_system_health,
    log_platform_event,
    organisation_queryset,
    organisation_usage,
    platform_dashboard_stats,
    renew_subscription_manually,
)


@platform_role_required()
def dashboard(request):
    context = {
        "stats": platform_dashboard_stats(),
        "subscription_alerts": expiring_subscription_alerts(),
        "organisations_recentes": organisation_queryset()[:6],
        "tickets_critiques": SupportTicket.objects.exclude(
            statut__in=[
                SupportTicket.Statut.RESOLU,
                SupportTicket.Statut.FERME,
            ]
        )
        .select_related("organisation", "responsable")
        .order_by("-priorite", "-created_at")[:6],
        "paiements_recents": PaiementAbonnement.objects.select_related(
            "abonnement__organisation",
            "abonnement__plan",
        )[:6],
        "health": live_system_health(),
    }
    return render(request, "platform_admin/dashboard.html", context)


@platform_role_required(
    PlatformStaffProfile.Role.OPS,
    PlatformStaffProfile.Role.FINANCE,
)
def organisation_create(request):
    form = PlatformOrganisationCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        (
            organisation,
            owner,
            temporary_password,
            abonnement,
            payment,
        ) = create_platform_organisation(form.cleaned_data, actor=request.user)
        login_url = request.build_absolute_uri(reverse("accounts:login"))
        organisation_url = request.build_absolute_uri(
            reverse(
                "organisations:owner-dashboard",
                kwargs={"organisation_slug": organisation.slug},
            )
        )
        email_sent = False
        if form.cleaned_data.get("envoyer_identifiants"):
            email_sent = (
                send_mail(
                    subject=f"Vos accès à {organisation.nom}",
                    message=(
                        f"Bonjour {owner.get_full_name() or owner.get_username()},\n\n"
                        f"Votre espace {organisation.nom} est prêt.\n"
                        f"Lien de connexion : {login_url}\n"
                        f"Matricule : {owner.get_username()}\n"
                        f"Mot de passe temporaire : {temporary_password}\n\n"
                        "Vous devrez modifier ce mot de passe à votre première connexion."
                    ),
                    from_email=None,
                    recipient_list=[owner.email],
                    fail_silently=True,
                )
                == 1
            )
        log_platform_event(
            request,
            PlatformAuditEvent.Type.ORGANISATION_CREATED,
            f"Organisation {organisation.nom} créée par l’équipe SahelTech.",
            organisation=organisation,
            object_type="Organisation",
            object_id=organisation.pk,
            metadata={
                "action": "platform_create",
                "activation": form.cleaned_data["activation"],
                "plan": abonnement.plan.code,
                "payment_id": payment.pk if payment else None,
                "credentials_email_sent": email_sent,
            },
        )
        return render(
            request,
            "platform_admin/organisation_created.html",
            {
                "organisation_obj": organisation,
                "owner": owner,
                "temporary_password": temporary_password,
                "login_url": login_url,
                "organisation_url": organisation_url,
                "email_sent": email_sent,
                "email_requested": form.cleaned_data.get("envoyer_identifiants"),
            },
        )
    return render(
        request,
        "platform_admin/organisation_form.html",
        {"form": form},
    )


@platform_role_required()
def organisation_list(request):
    organisations = organisation_queryset()
    if query := request.GET.get("q", "").strip():
        organisations = organisations.filter(
            Q(nom__icontains=query)
            | Q(email__icontains=query)
            | Q(slug__icontains=query)
        )
    if statut := request.GET.get("statut", "").strip():
        organisations = organisations.filter(statut=statut)
    return render(
        request,
        "platform_admin/organisation_list.html",
        {
            "organisations": organisations,
            "statuts": Organisation.Statut.choices,
        },
    )


@platform_role_required()
def organisation_detail(request, organisation_id):
    organisation = get_object_or_404(
        Organisation.objects.select_related("abonnement", "abonnement__plan"),
        pk=organisation_id,
    )
    return render(
        request,
        "platform_admin/organisation_detail.html",
        {
            "organisation_obj": organisation,
            "usage": organisation_usage(organisation),
            "membres": organisation.membres.select_related("user"),
            "plans": PlanAbonnement.objects.filter(is_active=True),
            "tickets": organisation.tickets_support.all()[:5],
            "backups": organisation.sauvegardes.all()[:5],
            "events": organisation.evenements_plateforme.select_related(
                "acteur"
            )[:10],
            "paiements": organisation.abonnement.paiements.all()[:10],
        },
    )


@platform_role_required(PlatformStaffProfile.Role.FINANCE)
def subscription_manual_payment(request, organisation_id):
    organisation = get_object_or_404(
        Organisation.objects.select_related("abonnement", "abonnement__plan"),
        pk=organisation_id,
    )
    abonnement = organisation.abonnement
    form = ManualSubscriptionPaymentForm(
        request.POST or None,
        abonnement=abonnement,
    )
    if request.method == "POST" and form.is_valid():
        abonnement, payment = renew_subscription_manually(
            abonnement,
            form.cleaned_data,
            actor=request.user,
        )
        log_platform_event(
            request,
            PlatformAuditEvent.Type.BILLING,
            (
                f"Paiement manuel {payment.reference} validé et abonnement de "
                f"{organisation.nom} renouvelé."
            ),
            organisation=organisation,
            object_type="PaiementAbonnement",
            object_id=payment.pk,
            metadata={
                "action": "manual_renewal",
                "amount": str(payment.montant),
                "period_end": abonnement.date_fin.isoformat(),
            },
        )
        messages.success(
            request,
            (
                f"Paiement {payment.reference} enregistré. "
                f"Abonnement actif jusqu’au {abonnement.date_fin:%d/%m/%Y}."
            ),
        )
        return redirect("platform_admin:organisation-detail", organisation.pk)
    return render(
        request,
        "platform_admin/manual_payment_form.html",
        {
            "organisation_obj": organisation,
            "abonnement": abonnement,
            "form": form,
        },
    )


@platform_role_required(
    PlatformStaffProfile.Role.SUPPORT,
    PlatformStaffProfile.Role.OPS,
    PlatformStaffProfile.Role.FINANCE,
)
@require_POST
def organisation_action(request, organisation_id):
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    action = request.POST.get("action")
    description = ""

    if action == "suspend":
        organisation.statut = Organisation.Statut.SUSPENDUE
        organisation.is_active = False
        organisation.save(update_fields=["statut", "is_active", "updated_at"])
        Abonnement.objects.filter(organisation=organisation).update(
            statut=Abonnement.Statut.SUSPENDU
        )
        description = f"Organisation {organisation.nom} suspendue."
    elif action == "reactivate":
        organisation.statut = Organisation.Statut.ACTIVE
        organisation.is_active = True
        organisation.save(update_fields=["statut", "is_active", "updated_at"])
        Abonnement.objects.filter(organisation=organisation).update(
            statut=Abonnement.Statut.ACTIF
        )
        description = f"Organisation {organisation.nom} réactivée."
    elif action == "extend_trial":
        try:
            requested_days = int(request.POST.get("days", 14))
        except (TypeError, ValueError):
            requested_days = 14
        days = max(1, min(requested_days, 365))
        base_date = max(organisation.date_fin_essai or timezone.now(), timezone.now())
        organisation.date_fin_essai = base_date + timedelta(days=days)
        organisation.statut = Organisation.Statut.ESSAI
        organisation.is_active = True
        organisation.save(
            update_fields=[
                "date_fin_essai",
                "statut",
                "is_active",
                "updated_at",
            ]
        )
        abonnement = getattr(organisation, "abonnement", None)
        if abonnement:
            abonnement.statut = Abonnement.Statut.ESSAI
            abonnement.date_fin = organisation.date_fin_essai
            abonnement.save(
                update_fields=["statut", "date_fin", "updated_at"]
            )
        description = f"Essai de {organisation.nom} prolongé de {days} jours."
    elif action == "archive":
        organisation.statut = Organisation.Statut.FERMEE
        organisation.is_active = False
        organisation.save(update_fields=["statut", "is_active", "updated_at"])
        description = f"Organisation {organisation.nom} archivée."
    elif action == "change_plan":
        if request.platform_role not in {
            PlatformStaffProfile.Role.SUPER_ADMIN,
            PlatformStaffProfile.Role.FINANCE,
        }:
            raise PermissionDenied("Action réservée à l’équipe Finance.")
        plan = get_object_or_404(
            PlanAbonnement,
            pk=request.POST.get("plan_id"),
            is_active=True,
        )
        abonnement = get_object_or_404(Abonnement, organisation=organisation)
        abonnement.plan = plan
        abonnement.montant = (
            plan.prix_annuel
            if abonnement.cycle == Abonnement.Cycle.ANNUEL
            else plan.prix_mensuel
        )
        abonnement.save(update_fields=["plan", "montant", "updated_at"])
        description = f"Plan de {organisation.nom} remplacé par {plan.nom}."
    elif action == "reset_owner_password":
        owner = (
            organisation.membres.select_related("user")
            .filter(
                role__in=[
                    MembreOrganisation.Role.PROPRIETAIRE,
                    MembreOrganisation.Role.ADMIN,
                ],
                is_active=True,
            )
            .first()
        )
        if not owner:
            messages.error(request, "Aucun administrateur actif trouvé.")
            return redirect("platform_admin:organisation-detail", organisation_id)
        temporary_password = get_random_string(14)
        owner.user.set_password(temporary_password)
        owner.user.must_change_password = True
        owner.user.save(
            update_fields=["password", "must_change_password", "updated_at"]
        )
        description = f"Mot de passe de {owner.user.get_username()} réinitialisé."
        messages.warning(
            request,
            f"Mot de passe temporaire : {temporary_password} — copiez-le maintenant.",
        )
    else:
        messages.error(request, "Action inconnue.")
        return redirect("platform_admin:organisation-detail", organisation_id)

    log_platform_event(
        request,
        PlatformAuditEvent.Type.ORGANISATION_UPDATED,
        description,
        organisation=organisation,
        object_type="Organisation",
        object_id=organisation.pk,
        metadata={"action": action},
    )
    messages.success(request, description)
    return redirect("platform_admin:organisation-detail", organisation_id)


@platform_role_required(
    PlatformStaffProfile.Role.SUPPORT,
    PlatformStaffProfile.Role.SUPER_ADMIN,
)
@require_POST
def impersonate_organisation(request, organisation_id):
    organisation = get_object_or_404(
        Organisation,
        pk=organisation_id,
        is_active=True,
    )
    owner = (
        organisation.membres.select_related("user")
        .filter(
            role__in=[
                MembreOrganisation.Role.PROPRIETAIRE,
                MembreOrganisation.Role.ADMIN,
            ],
            is_active=True,
            user__is_active=True,
        )
        .first()
    )
    if not owner:
        messages.error(request, "Aucun administrateur actif trouvé.")
        return redirect("platform_admin:organisation-detail", organisation_id)
    original_user_id = request.user.pk
    log_platform_event(
        request,
        PlatformAuditEvent.Type.IMPERSONATION,
        f"Début de connexion déléguée vers {owner.user.get_username()}.",
        organisation=organisation,
        severity=PlatformAuditEvent.Severite.WARNING,
        object_type="User",
        object_id=owner.user.pk,
    )
    login(
        request,
        owner.user,
        backend="accounts.authentication.EmailOrMatriculeBackend",
    )
    request.session["platform_original_user_id"] = original_user_id
    request.session["platform_impersonated_organisation_id"] = organisation.pk
    return redirect(
        "organisations:owner-dashboard",
        organisation_slug=organisation.slug,
    )


@require_POST
def stop_impersonation(request):
    original_user_id = request.session.get("platform_original_user_id")
    if not original_user_id:
        raise PermissionDenied("Aucune session déléguée active.")
    original_user = get_object_or_404(
        get_user_model(),
        pk=original_user_id,
        is_active=True,
        is_staff=True,
    )
    login(
        request,
        original_user,
        backend="accounts.authentication.EmailOrMatriculeBackend",
    )
    request.session.pop("platform_original_user_id", None)
    request.session.pop("platform_impersonated_organisation_id", None)
    messages.success(request, "Connexion déléguée terminée.")
    return redirect("platform_admin:dashboard")


@platform_role_required()
def export_organisation(request, organisation_id):
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    usage = organisation_usage(organisation)
    log_platform_event(
        request,
        PlatformAuditEvent.Type.ORGANISATION_UPDATED,
        f"Export de synthèse demandé pour {organisation.nom}.",
        organisation=organisation,
        object_type="Organisation",
        object_id=organisation.pk,
        metadata={"action": "export"},
    )
    return JsonResponse(
        {
            "organisation": {
                "id": organisation.pk,
                "nom": organisation.nom,
                "slug": organisation.slug,
                "email": organisation.email,
                "telephone": organisation.telephone,
                "statut": organisation.statut,
                "created_at": organisation.created_at.isoformat(),
            },
            "usage": usage,
        },
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )


@platform_role_required(
    PlatformStaffProfile.Role.FINANCE,
    PlatformStaffProfile.Role.LECTURE,
)
def subscriptions_view(request):
    abonnements = Abonnement.objects.select_related(
        "organisation", "plan"
    ).order_by("-updated_at")
    return render(
        request,
        "platform_admin/subscriptions.html",
        {
            "abonnements": abonnements,
            "plans": PlanAbonnement.objects.all(),
            "subscription_alerts": expiring_subscription_alerts(),
        },
    )


@platform_role_required(
    PlatformStaffProfile.Role.FINANCE,
    PlatformStaffProfile.Role.LECTURE,
)
def billing_view(request):
    return render(
        request,
        "platform_admin/billing.html",
        {
            "paiements": PaiementAbonnement.objects.select_related(
                "abonnement__organisation",
                "abonnement__plan",
            )[:100],
            "factures": SaaSInvoice.objects.select_related(
                "organisation", "abonnement__plan"
            )[:100],
            "coupons": Coupon.objects.all(),
            "revenu_total": PaiementAbonnement.objects.filter(
                statut=PaiementAbonnement.Statut.VALIDE
            ).aggregate(total=Sum("montant"))["total"]
            or Decimal("0"),
            "organisations": Organisation.objects.filter(
                abonnement__isnull=False,
                is_active=True,
            ).order_by("nom"),
        },
    )


@platform_role_required(
    PlatformStaffProfile.Role.SUPPORT,
    PlatformStaffProfile.Role.LECTURE,
)
def support_list(request):
    tickets = SupportTicket.objects.select_related(
        "organisation", "responsable"
    )
    if statut := request.GET.get("statut"):
        tickets = tickets.filter(statut=statut)
    if priorite := request.GET.get("priorite"):
        tickets = tickets.filter(priorite=priorite)
    return render(
        request,
        "platform_admin/support_list.html",
        {
            "tickets": tickets,
            "statuts": SupportTicket.Statut.choices,
            "priorites": SupportTicket.Priorite.choices,
        },
    )


@platform_role_required(PlatformStaffProfile.Role.SUPPORT)
def support_detail(request, ticket_id):
    ticket = get_object_or_404(
        SupportTicket.objects.select_related(
            "organisation", "responsable", "cree_par"
        ),
        pk=ticket_id,
    )
    form = SupportTicketUpdateForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        if message := request.POST.get("message", "").strip():
            TicketMessage.objects.create(
                ticket=ticket,
                auteur=request.user,
                message=message,
                is_internal=request.POST.get("is_internal") == "on",
            )
            ticket.derniere_reponse_at = timezone.now()
            ticket.save(update_fields=["derniere_reponse_at", "updated_at"])
        log_platform_event(
            request,
            PlatformAuditEvent.Type.SUPPORT,
            f"Ticket {ticket.numero} mis à jour.",
            organisation=ticket.organisation,
            object_type="SupportTicket",
            object_id=ticket.pk,
        )
        messages.success(request, "Ticket mis à jour.")
        return redirect("platform_admin:support-detail", ticket.pk)
    return render(
        request,
        "platform_admin/support_detail.html",
        {"ticket": ticket, "form": form},
    )


@platform_role_required()
def audit_view(request):
    events = PlatformAuditEvent.objects.select_related(
        "organisation", "acteur"
    )
    if organisation_id := request.GET.get("organisation"):
        events = events.filter(organisation_id=organisation_id)
    if event_type := request.GET.get("type"):
        events = events.filter(type_evenement=event_type)
    if query := request.GET.get("q", "").strip():
        events = events.filter(
            Q(description__icontains=query)
            | Q(adresse_ip__icontains=query)
            | Q(acteur__username__icontains=query)
        )
    return render(
        request,
        "platform_admin/audit.html",
        {
            "events": events[:250],
            "organisations": Organisation.objects.all(),
            "event_types": PlatformAuditEvent.Type.choices,
        },
    )


@platform_role_required(
    PlatformStaffProfile.Role.OPS,
    PlatformStaffProfile.Role.DEVELOPPEUR,
    PlatformStaffProfile.Role.LECTURE,
)
def monitoring_view(request):
    return render(
        request,
        "platform_admin/monitoring.html",
        {
            "health": live_system_health(),
            "metrics": SystemMetric.objects.all()[:30],
            "jobs": BackgroundJob.objects.all()[:30],
        },
    )


@platform_role_required(
    PlatformStaffProfile.Role.DEVELOPPEUR,
    PlatformStaffProfile.Role.OPS,
)
def feature_flags_view(request):
    form = FeatureFlagForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        flag = form.save()
        log_platform_event(
            request,
            PlatformAuditEvent.Type.SECURITY,
            f"Feature flag {flag.code} enregistrée.",
            object_type="FeatureFlag",
            object_id=flag.pk,
        )
        messages.success(request, "Feature flag enregistrée.")
        return redirect("platform_admin:feature-flags")
    return render(
        request,
        "platform_admin/feature_flags.html",
        {"flags": FeatureFlag.objects.prefetch_related("organisations"), "form": form},
    )


@platform_role_required(PlatformStaffProfile.Role.OPS)
def maintenance_view(request):
    maintenance_form = MaintenanceWindowForm(
        request.POST or None,
        prefix="maintenance",
    )
    announcement_form = AnnouncementForm(
        request.POST or None,
        prefix="announcement",
    )
    form_type = request.POST.get("form_type")
    if form_type == "maintenance" and maintenance_form.is_valid():
        window = maintenance_form.save()
        log_platform_event(
            request,
            PlatformAuditEvent.Type.MAINTENANCE,
            f"Maintenance {window.titre} enregistrée.",
            object_type="MaintenanceWindow",
            object_id=window.pk,
        )
        messages.success(request, "Maintenance enregistrée.")
        return redirect("platform_admin:maintenance")
    if form_type == "announcement" and announcement_form.is_valid():
        announcement_form.save()
        messages.success(request, "Annonce publiée.")
        return redirect("platform_admin:maintenance")
    return render(
        request,
        "platform_admin/maintenance.html",
        {
            "maintenances": MaintenanceWindow.objects.all()[:30],
            "announcements": Announcement.objects.all()[:30],
            "maintenance_form": maintenance_form,
            "announcement_form": announcement_form,
        },
    )


@platform_role_required(PlatformStaffProfile.Role.OPS)
def backups_view(request):
    if request.method == "POST":
        organisation = get_object_or_404(
            Organisation,
            pk=request.POST.get("organisation_id"),
        )
        backup = BackupRecord.objects.create(
            organisation=organisation,
            statut=BackupRecord.Statut.PLANIFIEE,
            lancee_par=request.user,
        )
        job = BackgroundJob.objects.create(
            nom=f"Sauvegarde de {organisation.nom}",
            queue="backups",
            payload={"backup_id": backup.pk, "organisation_id": organisation.pk},
        )
        log_platform_event(
            request,
            PlatformAuditEvent.Type.MAINTENANCE,
            f"Sauvegarde de {organisation.nom} planifiée.",
            organisation=organisation,
            object_type="BackupRecord",
            object_id=backup.pk,
        )
        try:
            create_tenant_backup(backup, job)
            messages.success(request, "Sauvegarde créée et prête au téléchargement.")
        except Exception:
            messages.error(
                request,
                "La sauvegarde a échoué. Consultez le journal de la tâche.",
            )
        return redirect("platform_admin:backups")
    return render(
        request,
        "platform_admin/backups.html",
        {
            "backups": BackupRecord.objects.select_related(
                "organisation", "lancee_par"
            )[:100],
            "organisations": Organisation.objects.filter(is_active=True),
        },
    )


@platform_role_required()
def analytics_view(request):
    return render(
        request,
        "platform_admin/analytics.html",
        {
            "stats": platform_dashboard_stats(),
            **analytics_data(),
        },
    )


@platform_role_required()
def settings_view(request):
    return render(
        request,
        "platform_admin/settings.html",
        {
            "staff_profiles": PlatformStaffProfile.objects.select_related(
                "user"
            ),
            "version": "1.0",
        },
    )
