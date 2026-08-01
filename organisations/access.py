from django.core.exceptions import PermissionDenied

from .models import MembreOrganisation

PERMISSION_CHOICES = (
    ("formations.manage", "Gerer les formations et sessions"),
    ("participants.manage", "Gerer les apprenants et inscriptions"),
    ("finance.view", "Consulter les paiements et mouvements"),
    ("finance.collect", "Enregistrer des encaissements"),
    ("finance.disburse", "Enregistrer des decaissements et transferts"),
    ("accounting.manage", "Gerer la comptabilite"),
    ("rh.manage", "Gerer les ressources humaines"),
    ("payroll.manage", "Gerer la paie salariale"),
    ("users.manage", "Gerer les utilisateurs et leurs acces"),
    ("settings.manage", "Modifier les parametres de l'entreprise"),
)

ALL_PERMISSIONS = frozenset(code for code, _ in PERMISSION_CHOICES)

ROLE_PERMISSIONS = {
    MembreOrganisation.Role.PROPRIETAIRE: ALL_PERMISSIONS,
    MembreOrganisation.Role.DIRECTEUR: ALL_PERMISSIONS,
    MembreOrganisation.Role.ADMIN: ALL_PERMISSIONS,
    MembreOrganisation.Role.RESPONSABLE: {
        "formations.manage", "participants.manage", "finance.view",
    },
    MembreOrganisation.Role.SECRETAIRE: {
        "formations.manage", "participants.manage", "finance.view",
        "finance.collect",
    },
    MembreOrganisation.Role.FORMATEUR: set(),
    MembreOrganisation.Role.COMPTABLE: {
        "finance.view", "finance.collect", "finance.disburse",
        "accounting.manage",
    },
    MembreOrganisation.Role.RH: {"rh.manage", "payroll.manage"},
    MembreOrganisation.Role.CAISSIER: {"finance.view", "finance.collect"},
    MembreOrganisation.Role.LECTURE: {"finance.view"},
}


def effective_permissions(member):
    if member is None or not member.is_active:
        return frozenset()
    permissions = set(ROLE_PERMISSIONS.get(member.role, set()))
    for code, enabled in (member.permissions_personnalisees or {}).items():
        if code not in ALL_PERMISSIONS:
            continue
        if enabled:
            permissions.add(code)
        else:
            permissions.discard(code)
    return frozenset(permissions)


def can_manage_members(request):
    if request.user.is_superuser:
        return True
    return "users.manage" in effective_permissions(
        getattr(request, "organisation_member", None)
    )


def require_member_permission(request, permission):
    if request.user.is_superuser:
        return
    member = getattr(request, "organisation_member", None)
    if permission not in effective_permissions(member):
        raise PermissionDenied("Vous n'avez pas l'autorisation d'effectuer cette action.")
