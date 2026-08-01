from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="membreorganisation",
            name="permissions_personnalisees",
            field=models.JSONField(blank=True, default=dict, help_text="Surcharges de permissions propres a cette entreprise."),
        ),
        migrations.AlterField(
            model_name="membreorganisation",
            name="role",
            field=models.CharField(choices=[("PROPRIETAIRE", "Proprietaire"), ("DIRECTEUR", "Directeur"), ("ADMIN", "Administrateur"), ("RESPONSABLE", "Responsable formation"), ("SECRETAIRE", "Secretaire"), ("FORMATEUR", "Formateur"), ("COMPTABLE", "Comptable"), ("RH", "Responsable RH"), ("CAISSIER", "Caissier"), ("LECTURE", "Lecture seule")], max_length=30),
        ),
        migrations.CreateModel(
            name="InvitationOrganisation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(choices=[("PROPRIETAIRE", "Proprietaire"), ("DIRECTEUR", "Directeur"), ("ADMIN", "Administrateur"), ("RESPONSABLE", "Responsable formation"), ("SECRETAIRE", "Secretaire"), ("FORMATEUR", "Formateur"), ("COMPTABLE", "Comptable"), ("RH", "Responsable RH"), ("CAISSIER", "Caissier"), ("LECTURE", "Lecture seule")], max_length=30)),
                ("permissions_personnalisees", models.JSONField(blank=True, default=dict)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("statut", models.CharField(choices=[("EN_ATTENTE", "En attente"), ("ACCEPTEE", "Acceptee"), ("ANNULEE", "Annulee"), ("EXPIREE", "Expiree")], db_index=True, default="EN_ATTENTE", max_length=20)),
                ("expire_le", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invitations_acceptees", to=settings.AUTH_USER_MODEL)),
                ("invited_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invitations_envoyees", to=settings.AUTH_USER_MODEL)),
                ("organisation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="organisations.organisation")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="invitationorganisation",
            index=models.Index(fields=["organisation", "statut"], name="organisatio_organis_c77176_idx"),
        ),
        migrations.AddIndex(
            model_name="invitationorganisation",
            index=models.Index(fields=["email", "statut"], name="organisatio_email_b3157f_idx"),
        ),
    ]
