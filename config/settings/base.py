import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-in-production")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps
    "core",
    "accounts",
    "organisations",
    "subscriptions",
    "platform_admin.apps.PlatformAdminConfig",
    "formations",
    "participants",
    "inscriptions",
    "operations",
    "paiements",
    "presences",
    "documents",
    "dashboard",
    "django_paie",
    "rest_framework",
    "django_rh.apps.RhConfig",
    "comptes.apps.ComptesConfig",
    "comptabilite_ohada.apps.ComptabiliteOhadaConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.AdminPathSecurityMiddleware",
    "accounts.middleware.MandatoryPasswordChangeMiddleware",
    "organisations.middleware.CurrentOrganisationMiddleware",
    "organisations.middleware.TenantRoleAccessMiddleware",
    "core.middleware.ModuleAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "builtins": ["core.templatetags.tenant_urls"],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "organisations.context_processors.current_organisation",
                "dashboard.context_processors.organisation",
                "platform_admin.context_processors.platform_status",
                "core.context_processors.modules",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.environ.get("TIME_ZONE", "Africa/Bamako")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    ("images", BASE_DIR / "static" / "images"),
    BASE_DIR / "static" / "src",
]
static_root = os.environ.get("APP_STATIC_ROOT")
if static_root:
    STATIC_ROOT = Path(static_root)
else:
    STATIC_ROOT = BASE_DIR / "static" / "dist"

MEDIA_URL = "/media/"
media_root = os.environ.get("APP_MEDIA_ROOT")
if media_root:
    MEDIA_ROOT = Path(media_root)
else:
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "accounts.authentication.EmailOrMatriculeBackend",
]
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/login/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
PUBLIC_APP_URL = "http://127.0.0.1:8000"
DEFAULT_FROM_EMAIL = "Formix <noreply@saheltech.tech>"

UNFOLD = {
    "SITE_TITLE": "SahelTech Platform Admin",
    "SITE_HEADER": "SahelTech",
    "SITE_SUBHEADER": "Administration et exploitation de la plateforme SaaS",
    "SITE_URL": "/platform/",
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "21 81 154",
            "600": "16 47 93",
            "700": "11 36 72",
            "800": "8 27 54",
            "900": "5 19 38",
            "950": "3 10 22",
        },
    },
}

DJANGO_PAIE = {
    "MODE": "SIMPLE",
    "EMPLOYE_MODEL": "django_rh.Employee",
    "CONTRAT_MODEL": None,
    "ABSENCE_MODEL": None,
    "RH_ADAPTER": None,
    "DEVISE": "FCFA",
    "MODE_PAR_ENTREPRISE": False,
    "JOUR_PAIEMENT": 5,
}

RH = {
    "AUTO_NUMBERING": True,
    "ENABLE_HISTORY": True,
    "ENABLE_AUDIT": True,
    "DEFAULT_CONTRACT_TYPE": "CDI",
}

COMPTABILITE_OHADA = {
    "API_ENABLED": True,
    "COMPTES_INTEGRATION_ENABLED": True,
    "DEVISE_PAR_DEFAUT": "FCFA",
    "AUTO_CREATE_JOURNAUX": True,
    "AUTO_CREATE_EXERCICE": True,
}

COMPTES = {
    "DEFAULT_CURRENCY": "XOF",
    "ALLOW_OVERDRAFT": False,
    "AUTO_CREATE_ACCOUNTING_ENTRIES": True,
}

# Sans ce bloc, DRF applique AllowAny par defaut : tout ViewSet qui oublie
# permission_classes devient accessible sans authentification. Le defaut doit
# etre ferme, et chaque API qui veut s'ouvrir doit le declarer explicitement.
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}
