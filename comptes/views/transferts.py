from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from organisations.utils import tenant_reverse

from ..models import Compte, TransfertCompte
from ..services import TransfertCompteService
from ..utils import scope_accounts


@login_required
def liste_transferts(request, **kwargs):
    transferts = TransfertCompte.objects.select_related(
        "source", "destination", "valide_par"
    ).filter(source__in=scope_accounts(request, Compte.objects.all())).order_by("-date")[:100]
    return render(request, "comptes/transfert_liste.html", {"transferts": transferts})


@login_required
@permission_required("comptes.add_transfertcompte", raise_exception=True)
def transfert_effectuer(request, **kwargs):
    if request.method == "POST":
        try:
            source = scope_accounts(request, Compte.objects).get(
                id=request.POST.get("source_id"), actif=True
            )
            destination = scope_accounts(request, Compte.objects).get(
                id=request.POST.get("dest_id"), actif=True
            )
            transfert = TransfertCompteService.transferer(
                source=source,
                destination=destination,
                montant=request.POST.get("montant"),
                user=request.user,
                notes=request.POST.get("notes", ""),
            )
            messages.success(
                request,
                f"Transfert de {transfert.montant:,.0f} FCFA effectué avec succès",
            )
            return redirect(tenant_reverse(request, "comptes:liste_transferts"))
        except Exception as exc:
            messages.error(request, str(exc))

    comptes = scope_accounts(request, Compte.objects.filter(actif=True)).order_by("code")
    return render(request, "comptes/transfert.html", {"comptes": comptes})
