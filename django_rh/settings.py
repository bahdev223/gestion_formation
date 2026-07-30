from django.conf import settings

DEFAULTS = {
    "AUTO_NUMBERING": True,
    "ENABLE_HISTORY": True,
    "ENABLE_AUDIT": True,
    "DEFAULT_CONTRACT_TYPE": "CDI",
}


def get_setting(name):
    val = getattr(settings, "RH", {}).get(name)
    if val is None:
        return DEFAULTS[name]
    return val
