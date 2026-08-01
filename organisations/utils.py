from django.core.exceptions import PermissionDenied
from django.urls import reverse

TENANT_NAMESPACES = {
    "formations": "formations",
    "participants": "participants",
    "inscriptions": "inscriptions",
    "operations": "operations",
    "paiements": "paiements",
    "presences": "presences",
    "documents": "documents",
    "django_paie": "paie",
    "dashboard": "dashboard",
    "comptabilite": "comptabilite",
    "comptes": "comptes",
}


def tenant_reverse(request, view_name, args=None, kwargs=None):
    organisation = getattr(request, "organisation", None)
    if organisation is None:
        raise RuntimeError("Une organisation est requise pour cette route métier.")

    if view_name == "organisations:owner-dashboard":
        tenant_view_name = view_name
    else:
        namespace, separator, route_name = view_name.partition(":")
        tenant_namespace = TENANT_NAMESPACES.get(namespace)
        tenant_view_name = (
            f"organisations:{tenant_namespace}:{route_name}"
            if separator and tenant_namespace
            else view_name
        )

    if args:
        return reverse(tenant_view_name, args=(organisation.slug, *args))
    return reverse(
        tenant_view_name,
        kwargs={"organisation_slug": organisation.slug, **(kwargs or {})},
    )


def get_request_organisation(request):
    """Retourne l'organisation courante ou None.

    Reserve aux contextes qui s'executent aussi hors espace client
    (context processors, pages publiques, console plateforme). Une vue metier
    doit utiliser require_request_organisation.
    """
    return getattr(request, "organisation", None)


def require_request_organisation(request):
    """Retourne l'organisation courante ou refuse l'acces.

    Toute vue metier doit passer par cette fonction : sans contexte tenant,
    un queryset non filtre exposerait les donnees de toutes les organisations.
    """
    organisation = getattr(request, "organisation", None)
    if organisation is None:
        raise PermissionDenied("Cette operation necessite un contexte organisation.")
    return organisation


def get_user_default_organisation(user):
    if not user or not user.is_authenticated:
        return None
    membership = (
        user.organisations.select_related("organisation")
        .filter(is_active=True, organisation__is_active=True)
        .exclude(organisation__statut__in=["SUSPENDUE", "FERMEE"])
        .order_by("organisation__nom")
        .first()
    )
    if membership is not None:
        return membership.organisation
    return None
