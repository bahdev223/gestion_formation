import re

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envoie un email de test SMTP pour valider la configuration d'envoi."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Email destinataire du test")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient):
            raise CommandError("L'adresse email fournie semble invalide.")

        if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER:
            raise CommandError(
                "EMAIL_HOST et EMAIL_HOST_USER doivent Ãªtre configurÃ©s pour tester "
                "l'envoi."
            )

        sent = send_mail(
            subject="[Formix] Test de configuration email",
            message=(
                "Ce message confirme que l'envoi SMTP Formix est fonctionnel.\n"
                f"Source : {settings.PUBLIC_APP_URL}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        if sent <= 0:
            raise CommandError("Aucun email n'a Ã©tÃ© envoyÃ©. VÃ©rifiez le transport SMTP.")

        self.stdout.write(self.style.SUCCESS("Email de test envoyÃ© avec succÃ¨s."))
