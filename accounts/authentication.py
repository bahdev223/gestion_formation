import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

logger = logging.getLogger(__name__)


class EmailOrMatriculeBackend(ModelBackend):
    """Authentifie un utilisateur par email ou matricule utilisateur.

    Le champ email de Django ne porte aucune contrainte d'unicité : un même
    email peut donc exister sur plusieurs comptes, ou correspondre au
    matricule d'un autre. L'implémentation précédente utilisait get() et
    renvoyait None sur MultipleObjectsReturned, ce qui produisait un
    « identifiants incorrects » sans que le mot de passe soit testé, et sans
    aucune trace dans les journaux. On teste desormais chaque candidat.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("identifier") or "").strip()
        if not identifier or password is None:
            return None

        UserModel = get_user_model()
        candidats = list(
            UserModel._default_manager.filter(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            )
        )

        if not candidats:
            # Compare quand même pour ne pas révéler l'existence du compte par
            # le temps de reponse.
            UserModel().set_password(password)
            return None

        if len(candidats) > 1:
            logger.warning(
                "L'identifiant %r correspond à %d comptes (%s) : "
                "vérifiez les doublons d'email.",
                identifier,
                len(candidats),
                ", ".join(str(candidat.pk) for candidat in candidats),
            )

        reference = identifier.lower()
        candidats.sort(
            key=lambda u: (
                0 if (u.get_username() or "").lower() == reference else 1,
                0 if (u.email or "").lower() == reference else 1,
                u.pk,
            )
        )

        inactif_reconnu = False
        for candidat in candidats:
            if not candidat.check_password(password):
                continue
            if self.user_can_authenticate(candidat):
                return candidat
            inactif_reconnu = True

        if inactif_reconnu:
            logger.warning(
                "Connexion refusée pour %r : le mot de passe est correct mais "
                "le compte est désactivé.",
                identifier,
            )
        return None
