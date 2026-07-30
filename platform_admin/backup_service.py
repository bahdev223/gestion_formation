import hashlib
import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.apps import apps
from django.core import serializers
from django.core.files.base import ContentFile
from django.db.models import ForeignKey, OneToOneField
from django.utils import timezone

from subscriptions.models import PaiementAbonnement

from .models import BackgroundJob, BackupRecord


def _organisation_querysets(organisation):
    yield organisation.__class__.objects.filter(pk=organisation.pk)
    included_labels = {organisation._meta.label_lower}
    for model in apps.get_models():
        if model._meta.label_lower in included_labels:
            continue
        organisation_field = next(
            (
                field
                for field in model._meta.get_fields()
                if field.name == "organisation"
                and isinstance(field, (ForeignKey, OneToOneField))
            ),
            None,
        )
        if organisation_field is not None:
            included_labels.add(model._meta.label_lower)
            yield model._default_manager.filter(organisation=organisation)

    yield PaiementAbonnement.objects.filter(
        abonnement__organisation=organisation
    )
    user_ids = organisation.membres.values_list("user_id", flat=True)
    yield apps.get_model("accounts", "User").objects.filter(pk__in=user_ids)


def create_tenant_backup(backup, job=None):
    backup.statut = BackupRecord.Statut.EN_COURS
    backup.started_at = timezone.now()
    backup.save(update_fields=["statut", "started_at", "updated_at"])
    if job:
        job.statut = BackgroundJob.Statut.EN_COURS
        job.started_at = timezone.now()
        job.progression = 10
        job.save(
            update_fields=[
                "statut",
                "started_at",
                "progression",
                "updated_at",
            ]
        )

    try:
        records = []
        for queryset in _organisation_querysets(backup.organisation):
            records.extend(
                json.loads(serializers.serialize("json", queryset))
            )
        manifest = {
            "format": "saheltech-tenant-backup-v1",
            "organisation_id": backup.organisation_id,
            "organisation_slug": backup.organisation.slug,
            "created_at": timezone.now().isoformat(),
            "record_count": len(records),
        }
        archive_buffer = BytesIO()
        with ZipFile(archive_buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            archive.writestr(
                "data.json",
                json.dumps(records, ensure_ascii=False),
            )
        payload = archive_buffer.getvalue()
        filename = (
            f"{backup.organisation.slug}/"
            f"{timezone.now():%Y%m%d-%H%M%S}.zip"
        )
        backup.fichier.save(filename, ContentFile(payload), save=False)
        backup.taille_octets = len(payload)
        backup.checksum = hashlib.sha256(payload).hexdigest()
        backup.statut = BackupRecord.Statut.REUSSIE
        backup.completed_at = timezone.now()
        backup.erreur = ""
        backup.save()
        if job:
            job.statut = BackgroundJob.Statut.REUSSI
            job.progression = 100
            job.completed_at = timezone.now()
            job.resultat = {
                "backup_id": backup.pk,
                "record_count": len(records),
            }
            job.save()
    except Exception as exc:
        backup.statut = BackupRecord.Statut.ECHOUEE
        backup.erreur = str(exc)
        backup.completed_at = timezone.now()
        backup.save()
        if job:
            job.statut = BackgroundJob.Statut.ECHOUE
            job.erreur = str(exc)
            job.completed_at = timezone.now()
            job.save()
        raise
    return backup
