from django.db import DatabaseError

from .models import ConfigurationOrganisation


def organisation(request):
    try:
        configuration = ConfigurationOrganisation.objects.order_by("pk").first()
    except DatabaseError:
        configuration = None
    return {"organisation": configuration}

