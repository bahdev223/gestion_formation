"""Activation des modules par organisation.

Point d'entree unique cote application. La resolution reelle est faite par
subscriptions.services.FeatureService, qui fusionne deja deux sources :

- les fonctionnalites du plan d'abonnement (PlanAbonnement.fonctionnalites) ;
- les feature flags plateforme (activation globale, progressive par
  pourcentage, ou ciblee sur des organisations precises).

Ce module n'ajoute pas une troisieme source de verite : il expose seulement le
catalogue des modules, un decorateur pour les vues et un mixin pour les vues
generiques, afin que le menu et les controles d'acces s'appuient sur la meme
table de correspondance.
"""

from django.core.exceptions import PermissionDenied

# Modules de base : le coeur du produit, disponible pour toute organisation,
# y compris pendant la periode d'essai ou avant la creation d'un abonnement.
# Ce n'est pas le plan qui les limite mais les quotas (max_participants,
# max_formations_actives...) : le plan vend une capacite, pas l'acces au metier
# de la formation.
MODULES_DE_BASE = frozenset(
    {
        "dashboard",
        "parametres",
        "operations",
        "formations",
        "sessions",
        "participants",
        "inscriptions",
        "paiements",
        "presences",
        "documents",
    }
)

# Modules optionnels : ils definissent l'etendue metier et dependent du plan
# ou d'un feature flag cible. Les cles doivent exister dans
# PlanAbonnement.fonctionnalites (voir seed_saas.py).
MODULE_FEATURES = {
    "rh": "hr",
    "paie": "payroll",
    "comptabilite": "accounting",
    "tresorerie": "treasury",
    "api": "api",
}


def module_est_actif(organisation, module):
    """Indique si un module est disponible pour une organisation."""
    if module in MODULES_DE_BASE:
        return True
    code = MODULE_FEATURES.get(module)
    if code is None:
        # Module inconnu : on refuse plutot que d'ouvrir par defaut.
        return False
    if organisation is None:
        return False
    from subscriptions.services import FeatureService

    return FeatureService.has_feature(organisation, code)


def modules_actifs(organisation):
    """Ensemble des modules disponibles, pour construire le menu."""
    if organisation is None:
        return set()
    return set(MODULES_DE_BASE) | {
        module
        for module in MODULE_FEATURES
        if module_est_actif(organisation, module)
    }


def exiger_module(request, module):
    """Refuse l'acces si le module n'est pas actif pour l'organisation."""
    from organisations.utils import require_request_organisation

    organisation = require_request_organisation(request)
    if not module_est_actif(organisation, module):
        raise PermissionDenied(
            f"Le module « {module} » n'est pas inclus dans l'abonnement de "
            "cette entreprise."
        )
    return organisation


def module_required(module):
    """Decorateur pour les vues fonction.

    S'applique apres les decorateurs d'authentification et de permission :
    l'appartenance a l'organisation est verifiee par le middleware tenant, ce
    controle porte uniquement sur la souscription au module.
    """

    def decorateur(vue):
        from functools import wraps

        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            exiger_module(request, module)
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur


class ModuleRequiredMixin:
    """Equivalent du decorateur pour les vues generiques.

    Declarer `module_requis = "comptabilite"` sur la vue.
    """

    module_requis = None

    def dispatch(self, request, *args, **kwargs):
        if self.module_requis is None:
            raise ValueError(
                f"{type(self).__name__} utilise ModuleRequiredMixin sans "
                "definir module_requis."
            )
        exiger_module(request, self.module_requis)
        return super().dispatch(request, *args, **kwargs)
