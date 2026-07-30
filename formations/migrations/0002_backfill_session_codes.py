from uuid import uuid4

from django.db import migrations
from django.utils import timezone


def backfill_session_codes(apps, schema_editor):
    SessionFormation = apps.get_model("formations", "SessionFormation")
    for session in SessionFormation.objects.filter(code=""):
        session.code = (
            f"SES-{timezone.localdate():%Y%m%d}-"
            f"{uuid4().hex[:6].upper()}"
        )
        session.save(update_fields=["code"])


class Migration(migrations.Migration):
    dependencies = [("formations", "0001_initial")]

    operations = [
        migrations.RunPython(
            backfill_session_codes,
            migrations.RunPython.noop,
        )
    ]
