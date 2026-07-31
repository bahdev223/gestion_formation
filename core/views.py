import os

from django.conf import settings
from django.db import connections
from django.http import JsonResponse


def health_live(request):
    return JsonResponse({"status": "ok"})


def health_check(request):
    return health_live(request)


def health_ready(request):
    checks = {}
    database_ok = False
    media_ok = False

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        database_ok = True
    except Exception:
        checks["database"] = "unavailable"
    else:
        checks["database"] = "ok"

    media_root = str(settings.MEDIA_ROOT)
    media_path = os.path.abspath(media_root)
    media_writable = (
        os.path.isdir(media_path)
        and os.access(media_path, os.R_OK | os.W_OK | os.X_OK)
    )
    media_ok = bool(media_writable)
    checks["media"] = "ok" if media_writable else "unavailable"

    payload = {
        "status": "ok" if database_ok and media_ok else "degraded",
        "checks": checks,
    }

    if payload["status"] != "ok":
        return JsonResponse(payload, status=503)
    return JsonResponse(payload)
