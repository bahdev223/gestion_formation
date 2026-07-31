from django import template
from django.conf import settings
from django.core.files.storage import default_storage
from django.templatetags.static import static

register = template.Library()


def _normalize_default(fallback: str) -> str:
    if not fallback:
        return ""
    if fallback.startswith(("http://", "https://", "/")):
        return fallback
    return static(fallback)


def _file_exists(field_file):
    if not field_file:
        return False

    name = getattr(field_file, "name", None)
    if not name:
        return False

    media_name = str(name)
    if media_name.startswith(settings.MEDIA_URL):
        media_name = media_name[len(settings.MEDIA_URL) :]
    media_name = media_name.lstrip("/")

    try:
        storage = getattr(field_file, "storage", None) or default_storage
        return storage.exists(media_name)
    except Exception:
        return False


@register.filter
def media_safe_url(file_field, fallback=""):
    if not file_field:
        return _normalize_default(fallback)
    if not _file_exists(file_field):
        return _normalize_default(fallback)
    try:
        return file_field.url
    except Exception:
        return _normalize_default(fallback)


@register.filter
def media_file_exists(file_field):
    return bool(_file_exists(file_field))
