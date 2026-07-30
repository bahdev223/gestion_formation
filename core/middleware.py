from django.core.exceptions import PermissionDenied

from core.features import module_est_actif


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


# Prefixe d'URL sous /o/<slug>/ -> module requis. L'ordre compte : le premier
# prefixe correspondant gagne, donc les chemins les plus longs d'abord.
PREFIXES_MODULES = (
    ("api/comptes-financiers", "tresorerie"),
    ("comptes-financiers", "tresorerie"),
    ("ressources-humaines", "rh"),
    ("paie-salariale", "paie"),
    ("comptabilite", "comptabilite"),
    ("formations", "formations"),
    ("participants", "participants"),
    ("inscriptions", "inscriptions"),
    ("paiements", "paiements"),
    ("presences", "presences"),
    ("documents", "documents"),
)


class ModuleAccessMiddleware:
    """Refuse l'acces aux modules non inclus dans l'abonnement.

    Masquer une entree de menu ne protege rien : l'URL reste atteignable en la
    saisissant. Ce controle est place au niveau du routage plutot que sur
    chaque vue, pour deux raisons :

    - il couvre toutes les vues d'un module, y compris les API et les futures
      vues qu'on oublierait de decorer ;
    - il ne peut pas etre contourne par une nouvelle URL ajoutee plus tard.

    S'execute apres CurrentOrganisationMiddleware, qui a deja resolu
    request.organisation et verifie l'appartenance de l'utilisateur.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        organisation = getattr(request, "organisation", None)
        if organisation is not None:
            module = self._module_pour(request.path_info)
            if module and not module_est_actif(organisation, module):
                raise PermissionDenied(
                    f"Le module « {module} » n'est pas inclus dans "
                    "l'abonnement de cette entreprise."
                )
        return self.get_response(request)

    @staticmethod
    def _module_pour(chemin):
        parts = [part for part in chemin.split("/") if part]
        # /o/<slug>/<reste...>
        if len(parts) < 3 or parts[0] != "o":
            return None
        reste = "/".join(parts[2:])
        for prefixe, module in PREFIXES_MODULES:
            if reste == prefixe or reste.startswith(f"{prefixe}/"):
                return module
        return None
