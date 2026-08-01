import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite_ohada", "0004_regle_comptable"),
        ("organisations", "0002_access_management"),
    ]

    operations = [
        migrations.AddField(
            model_name="comptecomptable",
            name="organisation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="plan_comptable",
                to="organisations.organisation",
                verbose_name="Organisation",
            ),
        ),
        migrations.AlterField(
            model_name="comptecomptable",
            name="code",
            field=models.CharField(max_length=20, verbose_name="Code"),
        ),
        migrations.AddIndex(
            model_name="comptecomptable",
            index=models.Index(
                fields=["organisation", "code"],
                name="comptabili_organis_0cfa02_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="comptecomptable",
            constraint=models.UniqueConstraint(
                condition=Q(organisation__isnull=False),
                fields=("organisation", "code"),
                name="unique_compte_par_organisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="comptecomptable",
            constraint=models.UniqueConstraint(
                condition=Q(organisation__isnull=True),
                fields=("code",),
                name="unique_compte_modele",
            ),
        ),
    ]
