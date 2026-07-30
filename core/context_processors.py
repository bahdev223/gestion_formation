def project_settings(request):
    return {}


def modules(request):
    """Expose les modules actifs de l'organisation courante au menu.

    S'execute sur toutes les pages, y compris la landing publique et la console
    plateforme, ou il n'y a pas d'organisation : on renvoie alors un ensemble
    vide plutot que de lever une erreur.
    """
    from core.features import modules_actifs

    organisation = getattr(request, "organisation", None)
    if organisation is None:
        return {"modules_actifs": frozenset()}
    try:
        return {"modules_actifs": frozenset(modules_actifs(organisation))}
    except Exception:
        # Le menu ne doit jamais casser une page : en cas de probleme de
        # resolution (abonnement absent, base indisponible), on n'affiche que
        # les modules de base.
        from core.features import MODULES_DE_BASE

        return {"modules_actifs": frozenset(MODULES_DE_BASE)}
