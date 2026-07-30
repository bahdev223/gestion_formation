from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from documents.models import Attestation
from documents.services.pdf_service import render_pdf, replace_file
from presences.services.presence_service import calculate_attendance_rate


def attestation_eligibility(inscription):
    taux = Decimal(str(round(calculate_attendance_rate(inscription), 2)))
    reasons = []
    if inscription.statut != inscription.Statut.TERMINE:
        reasons.append("L'inscription doit être terminée.")
    if taux < inscription.session.seuil_presence_attestation:
        reasons.append(
            f"Le taux de présence ({taux} %) est inférieur au seuil "
            f"de {inscription.session.seuil_presence_attestation} %."
        )
    if (
        inscription.session.paiement_requis_attestation
        and inscription.reste_a_payer > 0
    ):
        reasons.append("Le paiement de la formation n'est pas soldé.")
    return not reasons, reasons, taux


def check_attestation_eligibility(inscription):
    eligible, _reasons, _taux = attestation_eligibility(inscription)
    return eligible


@transaction.atomic
def generate_attestation(inscription, user, organisation=None):
    eligible, reasons, taux = attestation_eligibility(inscription)
    if not eligible:
        raise ValidationError(" ".join(reasons))

    attestation, _created = Attestation.objects.update_or_create(
        inscription=inscription,
        defaults={
            "numero": getattr(
                getattr(inscription, "attestation", None), "numero", ""
            )
            or f"ATT-{timezone.localdate():%Y%m%d}-{uuid4().hex[:6].upper()}",
            "nom_participant": inscription.participant.nom_complet,
            "nom_formation": inscription.session.formation.nom,
            "titre_session": inscription.session.titre,
            "date_debut": inscription.session.date_debut,
            "date_fin": inscription.session.date_fin,
            "duree_texte": (
                f"{inscription.session.formation.duree} "
                f"{inscription.session.formation.get_unite_duree_display()}"
            ),
            "formateur_nom": (
                inscription.session.formateur.get_full_name()
                or inscription.session.formateur.username
            ),
            "taux_presence": taux,
            "generee_par": user,
            "organisation": organisation or inscription.organisation,
            "statut": Attestation.Statut.GENEREE,
            "motif_annulation": "",
        },
    )
    payload = render_pdf(
        "documents/pdf/attestation.html",
        {"attestation": attestation},
    )
    replace_file(
        attestation.fichier_pdf,
        f"{attestation.numero}.pdf",
        payload,
    )
    attestation.save()
    return attestation


@transaction.atomic
def cancel_attestation(attestation, reason, user):
    if not reason.strip():
        raise ValidationError("Le motif d'annulation est obligatoire.")
    attestation.statut = Attestation.Statut.ANNULEE
    attestation.motif_annulation = reason.strip()
    attestation.save(
        update_fields=["statut", "motif_annulation", "updated_at"]
    )
    return attestation
