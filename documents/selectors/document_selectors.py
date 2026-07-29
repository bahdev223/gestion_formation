from documents.models import Attestation


def get_attestations_for_inscription(inscription):
    return Attestation.objects.filter(inscription=inscription)

