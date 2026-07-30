from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "formix.saheltech.tech"]
CSRF_TRUSTED_ORIGINS = ["https://formix.saheltech.tech"]
PUBLIC_APP_URL = "http://127.0.0.1:8000"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Formix <noreply@saheltech.tech>"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
