from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import OrganisationScopedViewSetMixin

from ..models import (
    Compte, MouvementCompte, TransfertCompte,
    JournalCompte, RapprochementBancaire, ClotureCompte,
)
from ..services import (
    MouvementCompteService, TransfertCompteService,
    ClotureCompteService, CompteService,
)
from ..selectors import DashboardSelector, MouvementSelector
from .serializers import (
    CompteSerializer, MouvementCompteSerializer,
    TransfertCompteSerializer, JournalCompteSerializer,
    RapprochementBancaireSerializer, ClotureCompteSerializer,
)


class CompteViewSet(OrganisationScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Compte.objects.all()
    serializer_class = CompteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["type", "role", "actif", "devise"]
    search_fields = ["code", "nom"]

    @action(detail=True, methods=["post"])
    def recalculer_solde(self, request, pk=None, **kwargs):
        compte = self.get_object()
        nouveau_solde = CompteService.recalculer_solde(compte)
        return Response({"solde_actuel": nouveau_solde})

    @action(detail=True, methods=["get"])
    def historique(self, request, pk=None, **kwargs):
        compte = self.get_object()
        h = compte.historique.all().order_by("-created_at")[:50]
        data = [
            {
                "date": x.created_at.isoformat(),
                "type": x.type_changement,
                "ancien": x.ancienne_valeur,
                "nouveau": x.nouvelle_valeur,
            }
            for x in h
        ]
        return Response(data)

    @action(detail=False, methods=["get"])
    def synthese(self, request, **kwargs):
        # Sans tenant_filter, le selector agrege les comptes de toutes
        # les organisations.
        selector = DashboardSelector(
            tenant_filter={"organisation": self.get_organisation()}
        )
        return Response(selector.synthese_globale())


class MouvementCompteViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = MouvementCompte.objects.select_related("compte", "created_by")
    serializer_class = MouvementCompteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["compte", "nature", "statut"]
    search_fields = ["libelle", "reference"]

    def perform_create(self, serializer):
        # MouvementCompte ne porte pas de champ organisation : il est rattache
        # au tenant via son compte, deja filtre par le mixin.
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"])
    def encaisser(self, request, **kwargs):
        # compte_id vient du client : il doit etre resolu dans l'organisation
        # courante, sinon on encaisse sur le compte d'un autre tenant.
        compte = self.scoped_object(Compte, request.data.get("compte_id"))
        if compte is None:
            raise ValidationError({"compte_id": "Ce champ est obligatoire."})
        mvt = MouvementCompteService.encaisser(
            compte=compte,
            montant=request.data["montant"],
            libelle=request.data.get("libelle", ""),
            user=request.user,
            reference=request.data.get("reference", ""),
        )
        return Response(MouvementCompteSerializer(mvt).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def decaisser(self, request, **kwargs):
        compte = self.scoped_object(Compte, request.data.get("compte_id"))
        if compte is None:
            raise ValidationError({"compte_id": "Ce champ est obligatoire."})
        mvt = MouvementCompteService.decaisser(
            compte=compte,
            montant=request.data["montant"],
            libelle=request.data.get("libelle", ""),
            user=request.user,
            reference=request.data.get("reference", ""),
        )
        return Response(MouvementCompteSerializer(mvt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None, **kwargs):
        mvt = self.get_object()
        annulation = MouvementCompteService.annuler(
            mvt, user=request.user, raison=request.data.get("raison", "")
        )
        return Response(MouvementCompteSerializer(annulation).data)


class TransfertCompteViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = TransfertCompte.objects.select_related("source", "destination")
    serializer_class = TransfertCompteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def transferer(self, request, **kwargs):
        source = self.scoped_object(Compte, request.data.get("source_id"))
        destination = self.scoped_object(
            Compte, request.data.get("destination_id")
        )
        if source is None or destination is None:
            raise ValidationError(
                "source_id et destination_id sont obligatoires."
            )
        # Les deux comptes sont deja resolus dans l'organisation courante ;
        # cette verification protege contre une regression du scoping.
        if source.organisation_id != destination.organisation_id:
            raise ValidationError(
                "Les deux comptes doivent appartenir a la meme organisation."
            )
        if source.pk == destination.pk:
            raise ValidationError(
                "Le compte source et le compte destination sont identiques."
            )
        transfert = TransfertCompteService.transferer(
            source=source,
            destination=destination,
            montant=request.data["montant"],
            user=request.user,
            notes=request.data.get("notes", ""),
        )
        return Response(TransfertCompteSerializer(transfert).data, status=status.HTTP_201_CREATED)


class JournalCompteViewSet(
    OrganisationScopedViewSetMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = JournalCompte.objects.select_related("compte")
    serializer_class = JournalCompteSerializer
    permission_classes = [permissions.IsAuthenticated]


class RapprochementBancaireViewSet(
    OrganisationScopedViewSetMixin, viewsets.ModelViewSet
):
    queryset = RapprochementBancaire.objects.select_related("compte")
    serializer_class = RapprochementBancaireSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClotureCompteViewSet(
    OrganisationScopedViewSetMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = ClotureCompte.objects.select_related("compte", "cloture_par")
    serializer_class = ClotureCompteSerializer
    permission_classes = [permissions.IsAuthenticated]
