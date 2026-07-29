import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-in-production")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps
    "core",
    "accounts",
    "formations",
    "participants",
    "inscriptions",
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
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.organisation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    ("images", BASE_DIR / "static" / "images"),
    BASE_DIR / "static" / "src",
]
STATIC_ROOT = BASE_DIR / "static" / "dist"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

DJANGO_PAIE = {
    "MODE": "SIMPLE",
    "EMPLOYE_MODEL": "rh.Employee",
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
