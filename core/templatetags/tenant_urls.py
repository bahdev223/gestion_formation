from django import template
from django.urls import reverse

register = template.Library()


def _get_tenant(context):
    organisation = context.get("current_organisation")
    if organisation is None and context.get("request") is not None:
        organisation = getattr(context["request"], "organisation", None)
    return organisation


@register.simple_tag(takes_context=True)
def tenant_path(context, path=""):
    organisation = _get_tenant(context)
    cleaned = str(path or "").strip("/")
    if organisation is not None and getattr(organisation, "slug", ""):
        if cleaned:
            return f"/o/{organisation.slug}/{cleaned}/"
        return f"/o/{organisation.slug}/dashboard/"
    return f"/{cleaned}/" if cleaned else "/"


@register.simple_tag(takes_context=True)
def tenant_url(context, view_name, *args, **kwargs):
    organisation = _get_tenant(context)
    if organisation is not None and getattr(organisation, "slug", ""):
        if view_name == "organisations:owner-dashboard":
            tenant_view_name = view_name
        else:
            namespace, separator, route_name = view_name.partition(":")
            namespace_map = {
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
            tenant_namespace = namespace_map.get(namespace)
            tenant_view_name = (
                f"organisations:{tenant_namespace}:{route_name}"
                if separator and tenant_namespace
                else view_name
            )
        if args:
            return reverse(tenant_view_name, args=(organisation.slug, *args))
        tenant_kwargs = {"organisation_slug": organisation.slug, **kwargs}
        return reverse(tenant_view_name, kwargs=tenant_kwargs)
    return reverse(view_name, args=args, kwargs=kwargs)
