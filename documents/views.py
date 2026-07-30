from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from documents.models import Attestation, DocumentGenere
from documents.services.attestation_service import generate_attestation
from documents.services.generation_service import generate_document
from formations.models import Seance, SessionFormation
from inscriptions.models import Inscription
from organisations.utils import get_request_organisation, tenant_reverse
from paiements.models import Paiement


@login_required
@permission_required("documents.view_documentgenere", raise_exception=True)
def document_index(request, **kwargs):
    organisation = get_request_organisation(request)
    documents_qs = DocumentGenere.objects.select_related("genere_par")
    attestations_qs = Attestation.objects.select_related(
        "inscription", "generee_par"
    )
    paiements_qs = Paiement.objects.filter(statut=Paiement.Statut.VALIDE)
    sessions_qs = SessionFormation.objects.exclude(
        statut=SessionFormation.Statut.ANNULEE
    )
    seances_qs = Seance.objects.exclude(statut=Seance.Statut.ANNULEE)
    inscriptions_qs = Inscription.objects.filter(statut=Inscription.Statut.TERMINE)
    if organisation:
        documents_qs = documents_qs.filter(organisation=organisation)
        attestations_qs = attestations_qs.filter(organisation=organisation)
        paiements_qs = paiements_qs.filter(organisation=organisation)
        sessions_qs = sessions_qs.filter(organisation=organisation)
        seances_qs = seances_qs.filter(organisation=organisation)
        inscriptions_qs = inscriptions_qs.filter(organisation=organisation)
    return render(
        request,
        "documents/index.html",
        {
            "documents": documents_qs[:50],
            "attestations": attestations_qs[:30],
            "paiements": paiements_qs
            .select_related("inscription__participant")
            .order_by("-date_paiement")[:100],
            "sessions": sessions_qs.order_by("-date_debut")[:100],
            "seances": seances_qs
            .select_related("session")
            .order_by("-date")[:100],
            "inscriptions": inscriptions_qs
            .select_related(
                "participant", "session", "session__formation"
            )
            .order_by("-updated_at")[:100],
        },
    )


@login_required
@permission_required("documents.add_documentgenere", raise_exception=True)
@require_POST
def generate_receipt(request, **kwargs):
    organisation = get_request_organisation(request)
    paiements = Paiement.objects.select_related(
        "inscription__participant",
        "inscription__session__formation",
        "enregistre_par",
    )
    if organisation:
        paiements = paiements.filter(organisation=organisation)
    paiement = get_object_or_404(
        paiements,
        pk=request.POST.get("paiement_id"),
        statut=Paiement.Statut.VALIDE,
    )
    document = generate_document(
        document_type=DocumentGenere.TypeDocument.RECU,
        reference=paiement.numero_recu,
        template="documents/pdf/receipt.html",
        context={"paiement": paiement},
        user=request.user,
        organisation=organisation,
    )
    messages.success(request, "Le reçu PDF a été généré.")
    return redirect(
        tenant_reverse(request, "documents:download", kwargs={"document_id": document.pk})
    )


@login_required
@permission_required("documents.add_documentgenere", raise_exception=True)
@require_POST
def generate_participant_list(request, **kwargs):
    organisation = get_request_organisation(request)
    sessions = SessionFormation.objects.select_related("formation", "formateur")
    if organisation:
        sessions = sessions.filter(organisation=organisation)
    session = get_object_or_404(
        sessions,
        pk=request.POST.get("session_id"),
    )
    inscriptions = session.inscriptions.exclude(
        statut__in=[
            Inscription.Statut.ANNULE,
            Inscription.Statut.ABANDONNE,
        ]
    ).select_related("participant")
    document = generate_document(
        document_type=DocumentGenere.TypeDocument.LISTE_PARTICIPANTS,
        reference=session.code,
        template="documents/pdf/participant_list.html",
        context={"session": session, "inscriptions": inscriptions},
        user=request.user,
        organisation=organisation,
    )
    messages.success(request, "La liste des participants a été générée.")
    return redirect(
        tenant_reverse(request, "documents:download", kwargs={"document_id": document.pk})
    )


@login_required
@permission_required("documents.add_documentgenere", raise_exception=True)
@require_POST
def generate_attendance_sheet(request, **kwargs):
    organisation = get_request_organisation(request)
    seances = Seance.objects.select_related("session__formation")
    if organisation:
        seances = seances.filter(organisation=organisation)
    seance = get_object_or_404(
        seances,
        pk=request.POST.get("seance_id"),
    )
    inscriptions = seance.session.inscriptions.exclude(
        statut__in=[
            Inscription.Statut.ANNULE,
            Inscription.Statut.ABANDONNE,
        ]
    ).select_related("participant")
    document = generate_document(
        document_type=DocumentGenere.TypeDocument.FEUILLE_PRESENCE,
        reference=f"SEANCE-{seance.pk}",
        template="documents/pdf/attendance_sheet.html",
        context={"seance": seance, "inscriptions": inscriptions},
        user=request.user,
        organisation=organisation,
    )
    messages.success(request, "La feuille de présence PDF a été générée.")
    return redirect(
        tenant_reverse(request, "documents:download", kwargs={"document_id": document.pk})
    )


@login_required
@permission_required("documents.add_attestation", raise_exception=True)
@require_POST
def create_attestation(request, **kwargs):
    organisation = get_request_organisation(request)
    inscriptions = Inscription.objects.select_related(
        "participant", "session__formation", "session__formateur"
    )
    if organisation:
        inscriptions = inscriptions.filter(organisation=organisation)
    inscription = get_object_or_404(
        inscriptions,
        pk=request.POST.get("inscription_id"),
    )
    try:
        attestation = generate_attestation(
            inscription,
            request.user,
            organisation=organisation,
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(tenant_reverse(request, "documents:index"))
    messages.success(request, "L'attestation PDF a été générée.")
    return redirect(
        tenant_reverse(
            request,
            "documents:attestation-download",
            kwargs={"attestation_id": attestation.pk},
        )
    )


@login_required
@permission_required("documents.view_documentgenere", raise_exception=True)
def download_document(request, document_id, **kwargs):
    organisation = get_request_organisation(request)
    documents = DocumentGenere.objects.all()
    if organisation:
        documents = documents.filter(organisation=organisation)
    document = get_object_or_404(documents, pk=document_id)
    if not document.fichier:
        raise Http404("Fichier indisponible.")
    return FileResponse(
        document.fichier.open("rb"),
        as_attachment=True,
        filename=document.fichier.name.rsplit("/", 1)[-1],
    )


@login_required
@permission_required("documents.view_attestation", raise_exception=True)
def download_attestation(request, attestation_id, **kwargs):
    organisation = get_request_organisation(request)
    attestations = Attestation.objects.all()
    if organisation:
        attestations = attestations.filter(organisation=organisation)
    attestation = get_object_or_404(attestations, pk=attestation_id)
    if not attestation.fichier_pdf:
        raise Http404("Fichier indisponible.")
    return FileResponse(
        attestation.fichier_pdf.open("rb"),
        as_attachment=True,
        filename=f"{attestation.numero}.pdf",
    )
