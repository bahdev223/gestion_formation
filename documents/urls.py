from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_index, name="index"),
    path("generer/recu/", views.generate_receipt, name="generate-receipt"),
    path(
        "generer/liste-participants/",
        views.generate_participant_list,
        name="generate-participant-list",
    ),
    path(
        "generer/feuille-presence/",
        views.generate_attendance_sheet,
        name="generate-attendance-sheet",
    ),
    path(
        "generer/attestation/",
        views.create_attestation,
        name="generate-attestation",
    ),
    path(
        "telecharger/<int:document_id>/",
        views.download_document,
        name="download",
    ),
    path(
        "attestations/<int:attestation_id>/telecharger/",
        views.download_attestation,
        name="attestation-download",
    ),
]
