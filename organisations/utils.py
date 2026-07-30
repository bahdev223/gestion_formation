from django.urls import reverse

TENANT_NAMESPACES = {
    "formations": "formations",
    "participants": "participants",
    "inscriptions": "inscriptions",
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


def get_default_organisation():
    from organisations.models import Organisation

    return Organisation.objects.filter(slug="balys-group").first()


def get_request_organisation(request):
    return getattr(request, "organisation", None) or get_default_organisation()


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
    if user.is_superuser:
        return get_default_organisation()
    return None
