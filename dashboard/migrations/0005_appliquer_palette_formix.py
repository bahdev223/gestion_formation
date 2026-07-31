"""Applique la palette Formix aux organisations restees sur l'ancien bleu.

Les couleurs sont stockees par organisation, donc changer les valeurs par
defaut du modele ne modifie que les futures entreprises : celles qui existent
deja conservent le bleu enregistre a leur creation. Cette migration met a jour
uniquement les lignes dont la couleur correspond **exactement** a l'ancien
defaut, ce qui laisse intacte toute personnalisation deliberee.
"""

from django.db import migrations

ANCIENS = {
    "couleur_sidebar": "#0b2448",
    "couleur_primaire": "#15519a",
    "couleur_secondaire": "#102f5d",
    "couleur_accent": "#f28b16",
    "couleur_fond": "#f4f6f9",
}

NOUVEAUX = {
    "couleur_sidebar": "#1f1509",
    "couleur_primaire": "#c2600a",
    "couleur_secondaire": "#9c4a06",
    "couleur_accent": "#ef8a1c",
    "couleur_fond": "#f6f5f3",
}


def _remplacer(apps, source, cible):
    Configuration = apps.get_model("dashboard", "ConfigurationOrganisation")
    for configuration in Configuration.objects.all():
        modifies = []
        for champ, ancienne in source.items():
            actuelle = (getattr(configuration, champ, "") or "").lower()
            if actuelle == ancienne.lower():
                setattr(configuration, champ, cible[champ])
                modifies.append(champ)
        if modifies:
            configuration.save(update_fields=modifies)


def vers_formix(apps, schema_editor):
    _remplacer(apps, ANCIENS, NOUVEAUX)


def retour_bleu(apps, schema_editor):
    _remplacer(apps, NOUVEAUX, ANCIENS)


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_palette_formix_par_defaut"),
    ]

    operations = [
        migrations.RunPython(vers_formix, retour_bleu),
    ]
