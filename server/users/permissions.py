"""
Permissions for User management and access control.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAccountOwner(BasePermission):
    """Object-level permission to only allow owners of an account to edit it."""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user
