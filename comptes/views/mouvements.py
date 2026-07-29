from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from ..models import Compte, MouvementCompte, StatutMouvement
from ..services import MouvementCompteService


@login_required
def liste_mouvements(request):
    mouvements = MouvementCompte.objects.select_related(
        "compte", "created_by"
    ).order_by("-date")[:200]
    comptes = Compte.objects.filter(actif=True).order_by("code")
    context = {
        "mouvements": mouvements,
        "comptes": comptes,
        "statuts": StatutMouvement.choices,
    }
    return render(request, "comptes/mouvements.html", context)


@login_required
@permission_required("comptes.add_mouvementcompte", raise_exception=True)
def mouvement_encaisser(request):
    if request.method == "POST":
        try:
            compte = Compte.objects.get(id=request.POST.get("compte_id"), actif=True)
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
    return redirect("comptes:dashboard")


@login_required
@permission_required("comptes.add_mouvementcompte", raise_exception=True)
def mouvement_decaisser(request):
    if request.method == "POST":
        try:
            compte = Compte.objects.get(id=request.POST.get("compte_id"), actif=True)
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
    return redirect("comptes:dashboard")
