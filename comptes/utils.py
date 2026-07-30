from organisations.utils import get_request_organisation


def organisation_filter(request):
    organisation = get_request_organisation(request)
    if organisation is None:
        return {}
    return {"organisation": organisation}


def scope_accounts(request, queryset):
    filters = organisation_filter(request)
    if filters:
        return queryset.filter(**filters)
    return queryset
