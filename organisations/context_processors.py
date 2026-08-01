def current_organisation(request):
    from .access import effective_permissions

    member = getattr(request, "organisation_member", None)
    return {
        "current_organisation": getattr(request, "organisation", None),
        "current_organisation_member": member,
        "tenant_permissions": effective_permissions(member),
    }
