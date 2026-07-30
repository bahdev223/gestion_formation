from django.db import migrations, models

COMMERCIAL_NAMES = {
    "STARTER": "Basic",
    "PREMIUM": "Business",
    "PRO": "Enterprise",
}

PREVIOUS_NAMES = {
    "STARTER": "Starter",
    "PREMIUM": "Premium",
    "PRO": "Pro",
}


def rename_plans(apps, schema_editor):
    PlanAbonnement = apps.get_model("subscriptions", "PlanAbonnement")
    for code, name in COMMERCIAL_NAMES.items():
        PlanAbonnement.objects.filter(code=code).update(nom=name)


def restore_plan_names(apps, schema_editor):
    PlanAbonnement = apps.get_model("subscriptions", "PlanAbonnement")
    for code, name in PREVIOUS_NAMES.items():
        PlanAbonnement.objects.filter(code=code).update(nom=name)


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0002_module_features_par_plan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="planabonnement",
            name="code",
            field=models.CharField(
                choices=[
                    ("STARTER", "Basic"),
                    ("PREMIUM", "Business"),
                    ("PRO", "Enterprise"),
                ],
                max_length=20,
                unique=True,
            ),
        ),
        migrations.RunPython(rename_plans, restore_plan_names),
    ]
