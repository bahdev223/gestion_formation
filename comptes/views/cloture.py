from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from organisations.utils import tenant_reverse

from ..models import Compte, JournalCompte
from ..services import ClotureCompteService
from ..utils import scope_accounts


@login_required
@permission_required("comptes.add_cloturecompte", raise_exception=True)
def cloturer_compte(request, compte_id, **kwargs):
    compte = get_object_or_404(
        scope_accounts(request, Compte.objects.all()), id=compte_id, actif=True
    )

    if request.method == "POST":
        try:
            solde_reel = request.POST.get("solde_reel")
            commentaire = request.POST.get("commentaire", "")
            ClotureCompteService.cloturer(
                compte=compte,
                solde_reel=solde_reel,
                user=request.user,
                commentaire=commentaire,
            )
            messages.success(request, f"Clôture de {compte.nom} effectuée")
            return redirect(
                tenant_reverse(
                    request,
                    "comptes:journal_consulter",
                    kwargs={"compte_id": compte.id},
                )
            )
        except Exception as e:
            messages.error(request, str(e))

    journal_ouvert = JournalCompte.objects.filter(compte=compte, cloture=False).first()
    context = {
        "compte": compte,
        "journal": journal_ouvert,
    }
    return render(request, "comptes/cloture.html", context)
