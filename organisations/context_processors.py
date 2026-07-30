def current_organisation(request):
    return {
        "current_organisation": getattr(request, "organisation", None),
        "current_organisation_member": getattr(
            request,
            "organisation_member",
            None,
        ),
    }
