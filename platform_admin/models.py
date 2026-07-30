from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class PlatformStaffProfile(TimeStampedModel):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super administrateur"
        SUPPORT = "SUPPORT", "Support"
        FINANCE = "FINANCE", "Finance"
        OPS = "OPS", "Opérations"
        DEVELOPPEUR = "DEVELOPPEUR", "Développeur"
        LECTURE = "LECTURE", "Lecture seule"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LECTURE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    mfa_required = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Accès équipe SahelTech"
        verbose_name_plural = "Accès équipe SahelTech"

    def __str__(self):
        return f"{self.user.get_username()} — {self.get_role_display()}"


class SupportTicket(TimeStampedModel):
    class Priorite(models.TextChoices):
        BASSE = "BASSE", "Basse"
        NORMALE = "NORMALE", "Normale"
        HAUTE = "HAUTE", "Haute"
        CRITIQUE = "CRITIQUE", "Critique"

    class Statut(models.TextChoices):
        OUVERT = "OUVERT", "Ouvert"
        EN_COURS = "EN_COURS", "En cours"
        EN_ATTENTE = "EN_ATTENTE", "En attente du client"
        RESOLU = "RESOLU", "Résolu"
        FERME = "FERME", "Fermé"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_support",
    )
    titre = models.CharField(max_length=255)
    description = models.TextField()
    priorite = models.CharField(
        max_length=20,
        choices=Priorite.choices,
        default=Priorite.NORMALE,
        db_index=True,
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.OUVERT,
        db_index=True,
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_support_crees",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_support_assignes",
    )
    derniere_reponse_at = models.DateTimeField(null=True, blank=True)
    resolu_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ticket de support"
        verbose_name_plural = "Tickets de support"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = f"SUP-{timezone.localdate():%Y%m}-{uuid4().hex[:6].upper()}"
        if self.statut in {self.Statut.RESOLU, self.Statut.FERME} and not self.resolu_at:
            self.resolu_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} — {self.titre}"


class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    message = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message de support"
        verbose_name_plural = "Messages de support"


class PlatformAuditEvent(TimeStampedModel):
    class Type(models.TextChoices):
        LOGIN = "LOGIN", "Connexion"
        LOGIN_FAILED = "LOGIN_FAILED", "Échec de connexion"
        ORGANISATION_CREATED = "ORGANISATION_CREATED", "Création d'entreprise"
        ORGANISATION_UPDATED = "ORGANISATION_UPDATED", "Modification d'entreprise"
        SUBSCRIPTION = "SUBSCRIPTION", "Abonnement"
        BILLING = "BILLING", "Facturation"
        SUPPORT = "SUPPORT", "Support"
        IMPERSONATION = "IMPERSONATION", "Connexion déléguée"
        SECURITY = "SECURITY", "Sécurité"
        ERROR = "ERROR", "Erreur"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    class Severite(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Avertissement"
        ERROR = "ERROR", "Erreur"
        CRITICAL = "CRITICAL", "Critique"

    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evenements_plateforme",
    )
    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evenements_plateforme",
    )
    type_evenement = models.CharField(max_length=40, choices=Type.choices, db_index=True)
    severite = models.CharField(
        max_length=20,
        choices=Severite.choices,
        default=Severite.INFO,
        db_index=True,
    )
    description = models.TextField()
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    objet_type = models.CharField(max_length=100, blank=True)
    objet_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["type_evenement", "created_at"]),
            models.Index(fields=["organisation", "created_at"]),
        ]
        verbose_name = "Événement d'audit SaaS"
        verbose_name_plural = "Événements d'audit SaaS"


class FeatureFlag(TimeStampedModel):
    code = models.SlugField(max_length=80, unique=True)
    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_enabled_globally = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(default=0)
    organisations = models.ManyToManyField(
        "organisations.Organisation",
        blank=True,
        related_name="feature_flags",
    )

    class Meta:
        ordering = ["nom"]
        verbose_name = "Feature flag"
        verbose_name_plural = "Feature flags"

    def __str__(self):
        return self.nom

    def is_enabled_for(self, organisation):
        if self.is_enabled_globally:
            return True
        if not organisation:
            return False
        if self.organisations.filter(pk=organisation.pk).exists():
            return True
        if self.rollout_percentage:
            bucket = (organisation.pk * 2654435761) % 100
            return bucket < min(self.rollout_percentage, 100)
        return False


class Announcement(TimeStampedModel):
    class Audience(models.TextChoices):
        TOUS = "TOUS", "Tous les visiteurs"
        CLIENTS = "CLIENTS", "Entreprises clientes"
        PLATEFORME = "PLATEFORME", "Équipe SahelTech"

    titre = models.CharField(max_length=200)
    message = models.TextField()
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.CLIENTS,
    )
    niveau = models.CharField(
        max_length=20,
        choices=[
            ("INFO", "Information"),
            ("WARNING", "Avertissement"),
            ("CRITICAL", "Critique"),
        ],
        default="INFO",
    )
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"


class MaintenanceWindow(TimeStampedModel):
    class Statut(models.TextChoices):
        PLANIFIEE = "PLANIFIEE", "Planifiée"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminée"
        ANNULEE = "ANNULEE", "Annulée"

    titre = models.CharField(max_length=200)
    message = models.TextField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIEE,
        db_index=True,
    )
    bloque_inscriptions = models.BooleanField(default=False)
    affiche_banniere = models.BooleanField(default=True)

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "Fenêtre de maintenance"
        verbose_name_plural = "Fenêtres de maintenance"

    @property
    def is_current(self):
        now = timezone.now()
        return (
            self.statut in {self.Statut.PLANIFIEE, self.Statut.EN_COURS}
            and self.starts_at <= now <= self.ends_at
        )


class BackupRecord(TimeStampedModel):
    class Statut(models.TextChoices):
        PLANIFIEE = "PLANIFIEE", "Planifiée"
        EN_COURS = "EN_COURS", "En cours"
        REUSSIE = "REUSSIE", "Réussie"
        ECHOUEE = "ECHOUEE", "Échouée"

    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sauvegardes",
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIEE,
        db_index=True,
    )
    taille_octets = models.PositiveBigIntegerField(default=0)
    fichier = models.FileField(upload_to="platform/backups/", null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    erreur = models.TextField(blank=True)
    lancee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sauvegarde"
        verbose_name_plural = "Sauvegardes"


class BackgroundJob(TimeStampedModel):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_COURS = "EN_COURS", "En cours"
        REUSSI = "REUSSI", "Réussi"
        ECHOUE = "ECHOUE", "Échoué"
        ANNULE = "ANNULE", "Annulé"

    nom = models.CharField(max_length=200)
    queue = models.CharField(max_length=100, default="default")
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
    )
    progression = models.PositiveSmallIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    resultat = models.JSONField(default=dict, blank=True)
    erreur = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tâche de fond"
        verbose_name_plural = "Tâches de fond"


class Coupon(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    remise_pourcentage = models.PositiveSmallIntegerField(default=0)
    remise_montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_utilisations = models.PositiveIntegerField(null=True, blank=True)
    utilisations = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"


class SaaSInvoice(TimeStampedModel):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        EMISE = "EMISE", "Émise"
        PAYEE = "PAYEE", "Payée"
        EN_RETARD = "EN_RETARD", "En retard"
        ANNULEE = "ANNULEE", "Annulée"

    numero = models.CharField(max_length=50, unique=True, editable=False)
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.PROTECT,
        related_name="factures_saas",
    )
    abonnement = models.ForeignKey(
        "subscriptions.Abonnement",
        on_delete=models.PROTECT,
        related_name="factures",
    )
    paiement = models.ForeignKey(
        "subscriptions.PaiementAbonnement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="factures",
    )
    montant_ht = models.DecimalField(max_digits=12, decimal_places=2)
    taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=12, decimal_places=2)
    date_emission = models.DateField(default=timezone.localdate)
    date_echeance = models.DateField()
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        db_index=True,
    )

    class Meta:
        ordering = ["-date_emission", "-created_at"]
        verbose_name = "Facture SaaS"
        verbose_name_plural = "Factures SaaS"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = f"INV-{timezone.localdate():%Y%m}-{uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class SystemMetric(TimeStampedModel):
    cpu_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ram_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    disk_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    database_latency_ms = models.PositiveIntegerField(default=0)
    response_time_ms = models.PositiveIntegerField(default=0)
    errors_500 = models.PositiveIntegerField(default=0)
    queue_depth = models.PositiveIntegerField(default=0)
    database_ok = models.BooleanField(default=True)
    redis_ok = models.BooleanField(default=True)
    workers_ok = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mesure système"
        verbose_name_plural = "Mesures système"
