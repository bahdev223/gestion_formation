from django.db import migrations, models


def synchronize_legacy_identity(apps, schema_editor):
    Configuration = apps.get_model("dashboard", "ConfigurationOrganisation")
    Organisation = apps.get_model("organisations", "Organisation")
    legacy_names = {
        "BALY" + "'S " + "GROUP",
        "BALY" + "’S " + "GROUP",
    }
    for organisation in Organisation.objects.filter(nom__in=legacy_names):
        configured_name = (
            Configuration.objects.filter(organisation_id=organisation.pk)
            .exclude(nom__in=legacy_names)
            .exclude(nom="")
            .values_list("nom", flat=True)
            .first()
        )
        organisation.nom = configured_name or "Votre entreprise"
        organisation.save(update_fields=["nom"])
    for configuration in Configuration.objects.select_related("organisation"):
        fields = []
        if configuration.palette not in {
            "FORMIX", "OCEAN", "EMERALD", "BORDEAUX", "CUSTOM"
        }:
            configuration.palette = "FORMIX"
            fields.append("palette")
        if (
            configuration.organisation_id
            and configuration.nom != configuration.organisation.nom
        ):
            configuration.nom = configuration.organisation.nom
            fields.append("nom")
        if fields:
            configuration.save(update_fields=fields)


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0005_appliquer_palette_formix")]

    operations = [
        migrations.RunPython(synchronize_legacy_identity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="configurationorganisation",
            name="palette",
            field=models.CharField(
                choices=[
                    ("FORMIX", "Formix"),
                    ("OCEAN", "Ocean corporate"),
                    ("EMERALD", "Emerald finance"),
                    ("BORDEAUX", "Bordeaux premium"),
                    ("CUSTOM", "Personnalise"),
                ],
                default="FORMIX",
                max_length=20,
            ),
        ),
    ]
