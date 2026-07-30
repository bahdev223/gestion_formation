"""Ajoute les cles de modules de gestion aux plans existants.

Les modules RH, paie, comptabilite et tresorerie n'avaient aucune cle dans
PlanAbonnement.fonctionnalites : ils etaient donc visibles par toutes les
organisations, quel que soit leur plan. Maintenant que le menu et les vues
sont conditionnes, les plans deja en base doivent recevoir ces cles, sinon
has_feature() renverrait False et les modules disparaitraient sans que
personne ne l'ait decide.

Le decoupage par palier est une decision commerciale : il est modifiable
depuis l'administration ou en rejouant seed_saas.
"""

from django.db import migrations

MODULES_PAR_PLAN = {
    "STARTER": {
        "hr": False,
        "payroll": False,
        "accounting": False,
        "treasury": False,
    },
    "PREMIUM": {
        "hr": False,
        "payroll": False,
        "accounting": True,
        "treasury": True,
    },
    "PRO": {
        "hr": True,
        "payroll": True,
        "accounting": True,
        "treasury": True,
    },
}


def ajouter_cles_modules(apps, schema_editor):
    PlanAbonnement = apps.get_model("subscriptions", "PlanAbonnement")
    for plan in PlanAbonnement.objects.all():
        defauts = MODULES_PAR_PLAN.get(plan.code)
        if defauts is None:
            continue
        fonctionnalites = dict(plan.fonctionnalites or {})
        modifie = False
        for cle, valeur in defauts.items():
            # On ne remplace pas une valeur deja choisie explicitement.
            if cle not in fonctionnalites:
                fonctionnalites[cle] = valeur
                modifie = True
        if modifie:
            plan.fonctionnalites = fonctionnalites
            plan.save(update_fields=["fonctionnalites"])


def retirer_cles_modules(apps, schema_editor):
    PlanAbonnement = apps.get_model("subscriptions", "PlanAbonnement")
    cles = {"hr", "payroll", "accounting", "treasury"}
    for plan in PlanAbonnement.objects.all():
        fonctionnalites = dict(plan.fonctionnalites or {})
        restantes = {k: v for k, v in fonctionnalites.items() if k not in cles}
        if len(restantes) != len(fonctionnalites):
            plan.fonctionnalites = restantes
            plan.save(update_fields=["fonctionnalites"])


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(ajouter_cles_modules, retirer_cles_modules),
    ]
