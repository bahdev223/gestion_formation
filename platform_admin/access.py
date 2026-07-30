from functools import wraps

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import PlatformStaffProfile


def get_platform_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return PlatformStaffProfile.Role.SUPER_ADMIN
    if not user.is_staff:
        return None
    try:
        profile = user.platform_profile
    except PlatformStaffProfile.DoesNotExist:
        return None
    return profile.role if profile.is_active else None


def platform_role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={request.get_full_path()}")
            role = get_platform_role(request.user)
            if role is None:
                raise PermissionDenied("Accès réservé à l’équipe SahelTech.")
            if (
                allowed_roles
                and role != PlatformStaffProfile.Role.SUPER_ADMIN
                and role not in allowed_roles
            ):
                raise PermissionDenied("Votre rôle ne permet pas cette action.")
            request.platform_role = role
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


class PlatformAccessMixin(AccessMixin):
    allowed_platform_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = get_platform_role(request.user)
        if role is None:
            raise PermissionDenied("Accès réservé à l’équipe SahelTech.")
        if (
            self.allowed_platform_roles
            and role != PlatformStaffProfile.Role.SUPER_ADMIN
            and role not in self.allowed_platform_roles
        ):
            raise PermissionDenied("Votre rôle ne permet pas cette action.")
        request.platform_role = role
        return super().dispatch(request, *args, **kwargs)
