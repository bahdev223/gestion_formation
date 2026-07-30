from rest_framework.permissions import BasePermission


class RHAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_view")


class RHCreatePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_create")


class RHEditPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_edit")


class RHDeletePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_delete")


class RHPromotePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_promote")


class RHTransferPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_transfer")


class RHTerminatePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("rh.rh_terminate")
