from organisations.utils import require_request_organisation


def organisation_filter(request):
    return {"organisation": require_request_organisation(request)}


def scope_accounts(request, queryset):
    return queryset.filter(**organisation_filter(request))
