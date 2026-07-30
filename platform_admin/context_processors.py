from django.db.models import Q
from django.utils import timezone

from .access import get_platform_role
from .models import Announcement, MaintenanceWindow


def platform_status(request):
    now = timezone.now()
    audience = [Announcement.Audience.TOUS]
    if get_platform_role(request.user):
        audience.append(Announcement.Audience.PLATEFORME)
    elif request.user.is_authenticated:
        audience.append(Announcement.Audience.CLIENTS)
    announcements = Announcement.objects.filter(
        is_active=True,
        starts_at__lte=now,
        audience__in=audience,
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )
    maintenance = (
        MaintenanceWindow.objects.filter(
            affiche_banniere=True,
            statut__in=[
                MaintenanceWindow.Statut.PLANIFIEE,
                MaintenanceWindow.Statut.EN_COURS,
            ],
            ends_at__gte=now,
        )
        .order_by("starts_at")
        .first()
    )
    return {
        "platform_role": get_platform_role(request.user),
        "platform_announcements": announcements.distinct()[:3],
        "platform_maintenance": maintenance,
        "is_platform_impersonating": bool(
            request.session.get("platform_original_user_id")
        ),
    }
