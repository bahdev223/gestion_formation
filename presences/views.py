from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from formations.models import Seance
from inscriptions.models import Inscription
from organisations.utils import require_request_organisation, tenant_reverse
from presences.models import Presence
from presences.services.presence_service import save_presence


@login_required
@permission_required("presences.view_presence", raise_exception=True)
def presence_index(request, **kwargs):
    organisation = require_request_organisation(request)
    seances_qs = Seance.objects.select_related(
        "session", "session__formation"
    ).filter(organisation=organisation)
    seances = (
        seances_qs
        .annotate(
            nb_inscrits=Count(
                "session__inscriptions",
                filter=~Q(
                    session__inscriptions__statut__in=[
                        Inscription.Statut.ANNULE,
                        Inscription.Statut.ABANDONNE,
                    ]
                ),
                distinct=True,
            ),
            nb_saisis=Count("presences", distinct=True),
        )
        .order_by("-date", "-heure_debut")
    )
    return render(
        request,
        "presences/index.html",
        {
            "seances": seances,
            "total_seances": seances.count(),
            "seances_a_saisir": sum(
                1 for seance in seances if seance.nb_saisis < seance.nb_inscrits
            ),
        },
    )


@login_required
@permission_required("presences.view_presence", raise_exception=True)
@require_http_methods(["GET", "POST"])
def presence_sheet(request, seance_id, **kwargs):
    organisation = require_request_organisation(request)
    seances = Seance.objects.select_related(
        "session", "session__formation"
    ).filter(organisation=organisation)
    seance = get_object_or_404(
        seances,
        pk=seance_id,
    )
    inscriptions = list(
        seance.session.inscriptions.select_related("participant")
        .exclude(
            statut__in=[
                Inscription.Statut.ANNULE,
                Inscription.Statut.ABANDONNE,
            ]
        )
        .order_by("participant__nom", "participant__prenom")
    )

    if request.method == "POST":
        if not request.user.has_perm("presences.change_presence"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        saved = 0
        for inscription in inscriptions:
            statut = request.POST.get(f"statut_{inscription.pk}")
            if not statut:
                continue
            save_presence(
                seance=seance,
                inscription=inscription,
                status=statut,
                user=request.user,
                heure_arrivee=request.POST.get(
                    f"heure_arrivee_{inscription.pk}"
                )
                or None,
                motif=request.POST.get(f"motif_{inscription.pk}", "").strip(),
                observations=request.POST.get(
                    f"observations_{inscription.pk}", ""
                ).strip(),
            )
            saved += 1
        messages.success(
            request,
            f"{saved} présence(s) enregistrée(s) pour cette séance.",
        )
        return redirect(
            tenant_reverse(
                request,
                "presences:sheet",
                kwargs={"seance_id": seance.pk},
            )
        )

    presences = Presence.objects.filter(
        seance=seance,
        inscription__in=inscriptions,
        organisation=organisation,
    )
    existing = {
        item.inscription_id: item
        for item in presences
    }
    rows = [
        {"inscription": inscription, "presence": existing.get(inscription.pk)}
        for inscription in inscriptions
    ]
    return render(
        request,
        "presences/sheet.html",
        {
            "seance": seance,
            "rows": rows,
            "statuts": Presence.Statut.choices,
            "completed": len(existing),
        },
    )
