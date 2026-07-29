from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comptes", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mouvementcompte",
            name="object_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
