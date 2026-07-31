"""Verifie la configuration et l'accessibilite du stockage des medias.

A lancer dans le conteneur quand une image envoyee ne s'affiche pas :

    python manage.py diagnostiquer_medias
"""

import os
import shutil

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnostique le stockage des fichiers envoyes (MEDIA)."

    FICHIER_TEST = "diagnostic/ecriture-test.txt"

    def handle(self, *args, **options):
        ecrire = self.stdout.write

        ecrire(self.style.MIGRATE_HEADING("Configuration"))
        media_root = str(getattr(settings, "MEDIA_ROOT", "") or "")
        ecrire(f"  MEDIA_URL          : {getattr(settings, 'MEDIA_URL', '(absent)')}")
        ecrire(f"  MEDIA_ROOT         : {media_root or '(absent)'}")
        ecrire(f"  APP_MEDIA_ROOT     : {os.environ.get('APP_MEDIA_ROOT', '(non defini)')}")
        ecrire(f"  SERVE_MEDIA        : {os.environ.get('SERVE_MEDIA', '(non defini)')}")
        ecrire(f"  DEBUG              : {settings.DEBUG}")
        ecrire(f"  stockage par defaut: {default_storage.__class__.__name__}")

        if not media_root:
            ecrire(self.style.ERROR("  MEDIA_ROOT est vide : rien ne peut etre enregistre."))
            return

        ecrire("")
        ecrire(self.style.MIGRATE_HEADING("Repertoire"))
        existe = os.path.isdir(media_root)
        ecrire(f"  existe             : {existe}")
        if not existe:
            ecrire(
                self.style.ERROR(
                    "  Le repertoire est absent. Si un volume persistant est "
                    "monte, verifiez que son chemin correspond a MEDIA_ROOT."
                )
            )
            return
        ecrire(f"  accessible en ecriture : {os.access(media_root, os.W_OK)}")
        try:
            usage = shutil.disk_usage(media_root)
            libre_mo = usage.free // (1024 * 1024)
            ecrire(f"  espace libre       : {libre_mo} Mo")
            if libre_mo < 50:
                ecrire(self.style.WARNING("  Espace disque faible."))
        except OSError as exc:
            ecrire(self.style.WARNING(f"  espace libre indisponible : {exc}"))

        ecrire("")
        ecrire(self.style.MIGRATE_HEADING("Test d'ecriture puis de lecture"))
        try:
            if default_storage.exists(self.FICHIER_TEST):
                default_storage.delete(self.FICHIER_TEST)
            nom = default_storage.save(self.FICHIER_TEST, ContentFile(b"ok"))
            relu = default_storage.open(nom).read()
            url = default_storage.url(nom)
            ecrire(self.style.SUCCESS(f"  ecriture reussie   : {nom}"))
            ecrire(f"  relecture          : {relu!r}")
            ecrire(f"  URL generee        : {url}")
            default_storage.delete(nom)
            ecrire("  fichier de test supprime")
        except Exception as exc:
            ecrire(self.style.ERROR(f"  echec : {type(exc).__name__}: {exc}"))
            return

        ecrire("")
        ecrire(self.style.MIGRATE_HEADING("Fichiers deja presents"))
        self._lister(media_root)

        ecrire("")
        ecrire(
            "Pour les references en base pointant vers un fichier absent, "
            "utilisez la commande dediee :"
        )
        ecrire("  python manage.py media_audit")

    def _lister(self, media_root, limite=10):
        total = 0
        exemples = []
        for dossier, _, fichiers in os.walk(media_root):
            for fichier in fichiers:
                total += 1
                if len(exemples) < limite:
                    chemin = os.path.relpath(
                        os.path.join(dossier, fichier), media_root
                    )
                    exemples.append(chemin.replace(os.sep, "/"))
        self.stdout.write(f"  total              : {total}")
        for exemple in exemples:
            self.stdout.write(f"    - {exemple}")
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  Aucun fichier : soit rien n'a ete envoye, soit les "
                    "envois atterrissent ailleurs que dans MEDIA_ROOT."
                )
            )
