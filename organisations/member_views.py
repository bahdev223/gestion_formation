from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from subscriptions.services import QuotaService

from .access import PERMISSION_CHOICES, can_manage_members
from .forms import (
    InvitationAcceptForm,
    InvitationOrganisationForm,
    MembreOrganisationForm,
)
from .models import InvitationOrganisation, MembreOrganisation
from .utils import require_request_organisation, tenant_reverse


def _require_manager(request):
    if not can_manage_members(request):
        raise PermissionDenied("Seuls les responsables autorises gerent les acces.")


def _pending_invitation_count(organisation):
    return organisation.invitations.filter(
        statut=InvitationOrganisation.Statut.EN_ATTENTE,
        expire_le__gte=timezone.now(),
    ).count()


def _require_available_slot(organisation, exclude_invitation=None):
    usage = QuotaService.usage(organisation).get("utilisateurs")
    if not usage:
        raise ValidationError("Aucun abonnement actif ne permet d'ajouter un utilisateur.")
    pending = organisation.invitations.filter(
        statut=InvitationOrganisation.Statut.EN_ATTENTE,
        expire_le__gte=timezone.now(),
    )
    if exclude_invitation is not None:
        pending = pending.exclude(pk=exclude_invitation.pk)
    reserved = usage["used"] + pending.count()
    if reserved >= usage["limit"]:
        raise ValidationError("Le quota d'utilisateurs de votre offre est atteint.")


@login_required
def members_settings(request, **kwargs):
    _require_manager(request)
    organisation = require_request_organisation(request)
    members = organisation.membres.select_related("user", "invited_by").order_by(
        "user__first_name", "user__last_name", "user__username"
    )
    invitations = organisation.invitations.filter(
        statut=InvitationOrganisation.Statut.EN_ATTENTE,
        expire_le__gte=timezone.now(),
    ).select_related("invited_by")
    usage = QuotaService.usage(organisation).get("utilisateurs", {})
    return render(request, "organisations/members.html", {
        "members": members,
        "invitations": invitations,
        "usage": usage,
    })


@login_required
def invite_member(request, **kwargs):
    _require_manager(request)
    organisation = require_request_organisation(request)
    form = InvitationOrganisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            _require_available_slot(organisation)
            if organisation.membres.filter(user__email__iexact=form.cleaned_data["email"]).exists():
                raise ValidationError("Cet utilisateur appartient deja a l'entreprise.")
            organisation.invitations.filter(
                email__iexact=form.cleaned_data["email"],
                statut=InvitationOrganisation.Statut.EN_ATTENTE,
            ).update(statut=InvitationOrganisation.Statut.ANNULEE)
            invitation = form.save(commit=False)
            invitation.organisation = organisation
            invitation.invited_by = request.user
            invitation.expire_le = timezone.now() + timedelta(days=7)
            invitation.permissions_personnalisees = form.cleaned_permissions()
            invitation.save()
            invitation_url = request.build_absolute_uri(
                reverse("organisation-invitation-accept", args=[invitation.token])
            )
            messages.success(request, "Invitation creee. Copiez le lien pour l'envoyer au collaborateur.")
            return render(request, "organisations/invite_success.html", {
                "invitation": invitation,
                "invitation_url": invitation_url,
            })
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "organisations/invite_form.html", {
        "form": form,
        "permission_choices": PERMISSION_CHOICES,
    })


@login_required
def edit_member(request, member_id, **kwargs):
    _require_manager(request)
    organisation = require_request_organisation(request)
    member = get_object_or_404(organisation.membres.select_related("user"), pk=member_id)
    was_owner = member.role == MembreOrganisation.Role.PROPRIETAIRE
    form = MembreOrganisationForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        removing_owner = was_owner and (
            form.cleaned_data["role"] != MembreOrganisation.Role.PROPRIETAIRE
            or not form.cleaned_data["is_active"]
        )
        active_owners = organisation.membres.filter(
            role=MembreOrganisation.Role.PROPRIETAIRE, is_active=True
        ).count()
        if removing_owner and active_owners <= 1:
            form.add_error(None, "Le dernier proprietaire actif ne peut pas etre retire.")
        elif member.user_id == request.user.id and not form.cleaned_data["is_active"]:
            form.add_error(None, "Vous ne pouvez pas suspendre votre propre acces.")
        else:
            member = form.save(commit=False)
            member.permissions_personnalisees = form.cleaned_permissions()
            member.save()
            messages.success(request, "Les acces de l'utilisateur ont ete mis a jour.")
            return redirect(tenant_reverse(request, "organisations:members"))
    return render(request, "organisations/member_form.html", {
        "form": form,
        "member": member,
        "permission_choices": PERMISSION_CHOICES,
    })


@login_required
def cancel_invitation(request, invitation_id, **kwargs):
    _require_manager(request)
    organisation = require_request_organisation(request)
    invitation = get_object_or_404(
        organisation.invitations,
        pk=invitation_id,
        statut=InvitationOrganisation.Statut.EN_ATTENTE,
    )
    if request.method == "POST":
        invitation.statut = InvitationOrganisation.Statut.ANNULEE
        invitation.save(update_fields=["statut", "updated_at"])
        messages.success(request, "L'invitation a ete annulee.")
    return redirect(tenant_reverse(request, "organisations:members"))


@transaction.atomic
def accept_invitation(request, token):
    invitation = get_object_or_404(
        InvitationOrganisation.objects.select_related("organisation"), token=token
    )
    if not invitation.is_usable:
        if invitation.statut == InvitationOrganisation.Statut.EN_ATTENTE:
            invitation.statut = InvitationOrganisation.Statut.EXPIREE
            invitation.save(update_fields=["statut", "updated_at"])
        return render(request, "organisations/invitation_invalid.html", status=410)

    User = get_user_model()
    existing = User.objects.filter(email__iexact=invitation.email).first()
    if request.user.is_authenticated:
        if request.user.email.lower() != invitation.email.lower():
            raise PermissionDenied("Cette invitation est destinee a une autre adresse email.")
        user = request.user
        if request.method == "POST":
            _require_available_slot(invitation.organisation, invitation)
            MembreOrganisation.objects.update_or_create(
                organisation=invitation.organisation,
                user=user,
                defaults={
                    "role": invitation.role,
                    "is_active": True,
                    "invited_by": invitation.invited_by,
                    "permissions_personnalisees": invitation.permissions_personnalisees,
                },
            )
            invitation.statut = InvitationOrganisation.Statut.ACCEPTEE
            invitation.accepted_by = user
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["statut", "accepted_by", "accepted_at", "updated_at"])
            return redirect(f"/o/{invitation.organisation.slug}/dashboard/")
        form = None
    elif existing:
        login_url = reverse("accounts:login")
        return redirect(f"{login_url}?next={request.path}")
    else:
        form = InvitationAcceptForm(request.POST or None, email=invitation.email)
        if request.method == "POST" and form.is_valid():
            _require_available_slot(invitation.organisation, invitation)
            role_map = {
                MembreOrganisation.Role.COMPTABLE: "COMPTABLE",
                MembreOrganisation.Role.RH: "RH",
                MembreOrganisation.Role.CAISSIER: "CAISSIER",
                MembreOrganisation.Role.FORMATEUR: "FORMATEUR",
            }
            user = User.objects.create_user(
                username=form.cleaned_data["matricule"],
                email=invitation.email,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                password=form.cleaned_data["password1"],
                role=role_map.get(invitation.role, "RESPONSABLE"),
            )
            MembreOrganisation.objects.create(
                organisation=invitation.organisation,
                user=user,
                role=invitation.role,
                invited_by=invitation.invited_by,
                permissions_personnalisees=invitation.permissions_personnalisees,
            )
            invitation.statut = InvitationOrganisation.Statut.ACCEPTEE
            invitation.accepted_by = user
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["statut", "accepted_by", "accepted_at", "updated_at"])
            login(request, user, backend="accounts.authentication.EmailOrMatriculeBackend")
            return redirect(f"/o/{invitation.organisation.slug}/dashboard/")

    return render(request, "organisations/invitation_accept.html", {
        "invitation": invitation,
        "form": form,
    })
