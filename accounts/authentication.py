from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrMatriculeBackend(ModelBackend):
    """Authentifie un utilisateur par email ou matricule utilisateur."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("identifier") or "").strip()
        if not identifier or password is None:
            return None

        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
