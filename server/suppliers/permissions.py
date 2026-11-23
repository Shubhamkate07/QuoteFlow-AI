"""
Permissions for Supplier API endpoints.
Enforces that user is authenticated and is an active member of the resolved tenant organization.
"""

from rest_framework import permissions
from organizations.selectors import get_active_organization_for_request


class IsSupplierOrganizationMember(permissions.BasePermission):
    """
    Requires the user to be authenticated and to have an active membership
    in the organization context. Attaches the verified organization to request.organization.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Resolves active org and verifies membership, or raises PermissionDenied (403)
        org = get_active_organization_for_request(request)
        request.organization = org
        return True
