from django.db import transaction

from documents.models import Attestation


def check_attestation_eligibility(inscription):
    return inscription.statut == inscription.Statut.TERMINE


@transaction.atomic
def generate_attestation(inscription, user):
    return Attestation.objects.create(
        inscription=inscription,
        numero=f"ATT-{inscription.numero}",
        nom_participant=str(inscription.participant),
        nom_formation=inscription.session.formation.nom,
        titre_session=inscription.session.titre,
        date_debut=inscription.session.date_debut,
        date_fin=inscription.session.date_fin,
        duree_texte=str(inscription.session.formation.duree),
        formateur_nom=str(inscription.session.formateur),
        taux_presence=0,
        generee_par=user,
    )


@transaction.atomic
def cancel_attestation(attestation, reason, user):
    attestation.statut = Attestation.Statut.ANNULEE
    attestation.motif_annulation = reason
    attestation.save(update_fields=["statut", "motif_annulation", "updated_at"])
    return attestation

