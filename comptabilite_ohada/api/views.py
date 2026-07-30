from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.mixins import OrganisationScopedViewSetMixin
from organisations.utils import require_request_organisation

from ..models import (
    CompteComptable, EcritureComptable, LigneEcritureComptable,
    JournalComptable, ExerciceComptable, ConfigurationComptable,
    Immobilisation, PlanAmortissement,
)
from ..services.ecriture_service import EcritureService
from ..services.journal_service import BalanceService, GrandLivreService
from ..services.bilan_service import BilanService
from ..services.exercice_service import ExerciceService
from ..services.amortissement_service import AmortissementService
from .serializers import (
    CompteComptableSerializer, EcritureComptableSerializer,
    EcritureCreateSerializer, JournalComptableSerializer,
    ExerciceComptableSerializer, ConfigurationComptableSerializer,
    ImmobilisationSerializer, PlanAmortissementSerializer,
)


class CompteComptableViewSet(viewsets.ReadOnlyModelViewSet):
    """Plan comptable SYSCOHADA : referentiel partage entre organisations.

    En lecture seule cote client : le plan est charge depuis le fichier
    standard par la commande charger_plan_comptable. Sans cette restriction,
    un client pouvait modifier ou supprimer des comptes utilises par tous
    les autres.
    """

    queryset = CompteComptable.objects.all()
    serializer_class = CompteComptableSerializer
    filterset_fields = ["code", "nature", "type_compte", "categorie", "actif"]
    search_fields = ["code", "libelle"]

    @action(detail=True, methods=["get"])
    def solde(self, request, pk=None, **kwargs):
        compte = self.get_object()
        # Le compte est partage, mais son solde est propre a l'organisation :
        # sans ce filtre, le solde cumulait les ecritures de tous les clients.
        organisation = require_request_organisation(request)
        qs = LigneEcritureComptable.objects.filter(
            compte=compte,
            ecriture__validee=True,
            ecriture__organisation=organisation,
        )
        exercice_id = request.query_params.get("exercice")
        if exercice_id:
            exercice = get_object_or_404(
                ExerciceComptable, pk=exercice_id, organisation=organisation
            )
            qs = qs.filter(
                ecriture__date_ecriture__gte=exercice.date_debut,
                ecriture__date_ecriture__lte=exercice.date_fin,
            )
        total_debit = qs.aggregate(total=Sum("debit"))["total"] or 0
        total_credit = qs.aggregate(total=Sum("credit"))["total"] or 0
        return Response({"solde": float(total_debit) - float(total_credit)})


class EcritureComptableViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = EcritureComptable.objects.prefetch_related("lignes__compte").all()
    filterset_fields = ["validee", "journal", "exercice"]
    search_fields = ["reference", "libelle"]

    def get_serializer_class(self):
        if self.action == "create":
            return EcritureCreateSerializer
        return EcritureComptableSerializer

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None, **kwargs):
        ecriture = self.get_object()
        if ecriture.validee:
            return Response({"error": "Déjà validée"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            EcritureService.valider_ecriture(ecriture, request.user)
            return Response({"status": "validée"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None, **kwargs):
        ecriture = self.get_object()
        try:
            EcritureService.annuler_ecriture(ecriture, request.user)
            return Response({"status": "annulée"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _scoped_exercice(self, request):
        """Resout l'exercice demande dans l'organisation courante.

        Sans ce filtre, un exercice appartenant a une autre organisation
        pouvait etre passe aux services d'etats financiers.
        """
        return self.scoped_object(
            ExerciceComptable, request.query_params.get("exercice")
        )

    @action(detail=False, methods=["get"])
    def balance(self, request, **kwargs):
        organisation = self.get_organisation()
        service = BalanceService()
        data = service.balance(
            exercice=self._scoped_exercice(request),
            organisation=organisation,
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def grand_livre(self, request, **kwargs):
        organisation = self.get_organisation()
        service = GrandLivreService()
        data = service.grand_livre(
            compte_code=request.query_params.get("compte"),
            exercice=self._scoped_exercice(request),
            organisation=organisation,
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def bilan(self, request, **kwargs):
        organisation = self.get_organisation()
        service = BilanService()
        bilan = service.bilan(
            exercice=self._scoped_exercice(request),
            organisation=organisation,
        )
        return Response(bilan)

    @action(detail=False, methods=["get"])
    def compte_resultat(self, request, **kwargs):
        organisation = self.get_organisation()
        service = BilanService()
        resultat = service.compte_resultat(
            exercice=self._scoped_exercice(request),
            organisation=organisation,
        )
        return Response(resultat)


class JournalComptableViewSet(viewsets.ReadOnlyModelViewSet):
    """Journaux standards SYSCOHADA : referentiel partage, lecture seule."""

    queryset = JournalComptable.objects.all()
    serializer_class = JournalComptableSerializer
    filterset_fields = ["code", "actif"]
    search_fields = ["code", "libelle"]

    @action(detail=True, methods=["get"])
    def ecritures(self, request, pk=None, **kwargs):
        journal = self.get_object()
        # Le journal est partage : ses ecritures doivent etre limitees au
        # tenant courant.
        ecritures = EcritureComptable.objects.filter(
            journal=journal,
            organisation=require_request_organisation(request),
        )
        page = self.paginate_queryset(ecritures)
        if page is not None:
            serializer = EcritureComptableSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = EcritureComptableSerializer(ecritures, many=True)
        return Response(serializer.data)


class ExerciceComptableViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = ExerciceComptable.objects.all()
    serializer_class = ExerciceComptableSerializer
    filterset_fields = ["cloture"]
    search_fields = ["code"]

    @action(detail=True, methods=["post"])
    def cloturer(self, request, pk=None, **kwargs):
        exercice = self.get_object()
        try:
            ExerciceService.cloturer(exercice, request.user)
            return Response({"status": "clôturé"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def rouvrir(self, request, pk=None, **kwargs):
        exercice = self.get_object()
        try:
            ExerciceService.rouvrir(exercice)
            return Response({"status": "rouvert"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ConfigurationComptableViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = ConfigurationComptable.objects.all()
    serializer_class = ConfigurationComptableSerializer


class ImmobilisationViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = Immobilisation.objects.prefetch_related("plan_amortissement").all()
    serializer_class = ImmobilisationSerializer
    filterset_fields = ["statut", "type_immobilisation"]
    search_fields = ["libelle", "code"]

    @action(detail=True, methods=["post"])
    def calculer_amortissement(self, request, pk=None, **kwargs):
        immobilisation = self.get_object()
        try:
            AmortissementService.generer_plan_amortissement(immobilisation, request.user)
            return Response({"status": "plan généré"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def comptabiliser_amortissement(self, request, pk=None, **kwargs):
        immobilisation = self.get_object()
        try:
            AmortissementService.comptabiliser_amortissement(immobilisation, request.user)
            return Response({"status": "amortissement comptabilisé"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
