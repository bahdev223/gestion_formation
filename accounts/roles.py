from django.contrib.auth.models import Group, Permission

ROLE_GROUPS = {
    "ADMIN": "Administrateurs",
    "RESPONSABLE": "Responsables formation",
    "FORMATEUR": "Formateurs",
    "COMPTABLE": "Comptables",
    "RH": "Ressources humaines",
    "CAISSIER": "Caissiers",
}

PROJECT_APPS = {
    "accounts",
    "organisations",
    "subscriptions",
    "formations",
    "participants",
    "inscriptions",
    "operations",
    "paiements",
    "presences",
    "documents",
    "dashboard",
    "rh",
    "django_paie",
    "comptes",
    "comptabilite_ohada",
}

ROLE_RULES = {
    "RESPONSABLE": {
        "formations": {"add", "change", "view"},
        "participants": {"add", "change", "view"},
        "inscriptions": {"add", "change", "view"},
        "operations": {"add", "change", "view"},
        "paiements": {"add", "change", "view"},
        "presences": {"add", "change", "view"},
        "documents": {"add", "change", "view"},
        "dashboard": {"view", "change"},
    },
    "FORMATEUR": {
        "formations": {"view"},
        "participants": {"view"},
        "inscriptions": {"view"},
        "presences": {"add", "change", "view"},
        "documents": {"view"},
    },
    "COMPTABLE": {
        "operations": {"add", "change", "view"},
        "paiements": {"add", "change", "view"},
        "documents": {"add", "view"},
        "comptes": {"add", "change", "view"},
        "comptabilite_ohada": {"add", "change", "view"},
        "django_paie": {"view"},
    },
    "RH": {
        "rh": {"add", "change", "view"},
        "django_paie": {"add", "change", "view"},
        "accounts": {"view", "change"},
    },
    "CAISSIER": {
        "participants": {"view"},
        "inscriptions": {"view"},
        "paiements": {"add", "view"},
        "operations": {"add", "view"},
        "documents": {"add", "view"},
        "comptes": {"add", "view"},
    },
}


def sync_role_groups():
    groups = {
        role: Group.objects.get_or_create(name=name)[0]
        for role, name in ROLE_GROUPS.items()
    }
    groups["ADMIN"].permissions.set(
        Permission.objects.filter(content_type__app_label__in=PROJECT_APPS)
    )
    for role, rules in ROLE_RULES.items():
        permissions = Permission.objects.none()
        for app_label, actions in rules.items():
            action_query = None
            from django.db.models import Q

            for action in actions:
                query = Q(codename__startswith=f"{action}_")
                action_query = (
                    query if action_query is None else action_query | query
                )
            permissions = permissions | Permission.objects.filter(
                action_query,
                content_type__app_label=app_label,
            )
        groups[role].permissions.set(permissions.distinct())
    from django.apps import apps

    User = apps.get_model("accounts", "User")
    managed_names = set(ROLE_GROUPS.values())
    for user in User.objects.all().only("id", "role", "is_superuser"):
        if user.is_superuser and user.role != "ADMIN":
            User.objects.filter(pk=user.pk).update(role="ADMIN")
            user.role = "ADMIN"
        target = groups.get(user.role)
        if target:
            user.groups.remove(*user.groups.filter(name__in=managed_names))
            user.groups.add(target)
    return groups
