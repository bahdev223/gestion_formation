from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from organisations.utils import tenant_reverse

from ..models import Compte, MouvementCompte, NatureMouvement, StatutMouvement
from ..services import MouvementCompteService
from ..utils import scope_accounts


@login_required
def liste_mouvements(request, **kwargs):
    mouvements = MouvementCompte.objects.select_related(
        "compte", "created_by"
    ).filter(compte__in=scope_accounts(request, Compte.objects.all()))
    compte_id = request.GET.get("compte")
    nature = request.GET.get("nature")
    statut = request.GET.get("statut")
    utilisateur_id = request.GET.get("utilisateur")
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    if compte_id:
        mouvements = mouvements.filter(compte_id=compte_id)
    if nature:
        mouvements = mouvements.filter(nature=nature)
    if statut:
        mouvements = mouvements.filter(statut=statut)
    if utilisateur_id:
        mouvements = mouvements.filter(created_by_id=utilisateur_id)
    if date_debut:
        mouvements = mouvements.filter(date__date__gte=date_debut)
    if date_fin:
        mouvements = mouvements.filter(date__date__lte=date_fin)
    mouvements = mouvements.order_by("-date")[:200]
    comptes = scope_accounts(request, Compte.objects.filter(actif=True)).order_by("code")
    organisation = request.organisation
    context = {
        "mouvements": mouvements,
        "comptes": comptes,
        "utilisateurs": organisation.membres.filter(is_active=True).select_related("user"),
        "natures": NatureMouvement.choices,
        "statuts": StatutMouvement.choices,
        "filters": request.GET,
        "payment_currency": organisation.devise,
    }
    return render(request, "comptes/mouvements.html", context)


@login_required
@permission_required("comptes.add_mouvementcompte", raise_exception=True)
def mouvement_encaisser(request, **kwargs):
    if request.method == "POST":
        try:
            compte = scope_accounts(request, Compte.objects).get(
                id=request.POST.get("compte_id"), actif=True
            )
            mouvement = MouvementCompteService.encaisser(
                compte=compte,
                montant=request.POST.get("montant"),
                libelle=request.POST.get("libelle", "Encaissement"),
                user=request.user,
                reference=request.POST.get("reference", ""),
            )
            messages.success(
                request,
                f"Encaissement de {mouvement.montant:,.0f} FCFA effectué",
            )
        except Exception as exc:
            messages.error(request, str(exc))
    return redirect(tenant_reverse(request, "comptes:dashboard"))


@login_required
@permission_required("comptes.add_mouvementcompte", raise_exception=True)
def mouvement_decaisser(request, **kwargs):
    if request.method == "POST":
        try:
            compte = scope_accounts(request, Compte.objects).get(
                id=request.POST.get("compte_id"), actif=True
            )
            mouvement = MouvementCompteService.decaisser(
                compte=compte,
                montant=request.POST.get("montant"),
                libelle=request.POST.get("libelle", "Décaissement"),
                user=request.user,
                reference=request.POST.get("reference", ""),
            )
            messages.success(
                request,
                f"Décaissement de {mouvement.montant:,.0f} FCFA effectué",
            )
        except Exception as exc:
            messages.error(request, str(exc))
    return redirect(tenant_reverse(request, "comptes:dashboard"))
