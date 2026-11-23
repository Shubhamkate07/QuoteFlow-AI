"""
Permissions for RFQ workflows and line item management.
Ensures cross-organization operations are strictly prevented.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from organizations.selectors import get_active_organization_for_request
from organizations.models import OrganizationMembership, OrganizationRole


class IsRFQOrganizationMember(BasePermission):
    """
    Guarantees the requesting user belongs to the active organization
    and has permissions for the requested action.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            organization = get_active_organization_for_request(request)
            request.organization = organization
        except Exception:
            return False

        # Read-only actions permitted for any active member
        if request.method in SAFE_METHODS:
            return True

        # Modification actions (create/update/delete)
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True,
        ).exists()

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Ensure object belongs strictly to the authenticated organization
        obj_org = getattr(obj, 'organization', None)
        if not obj_org and hasattr(obj, 'rfq'):
            obj_org = obj.rfq.organization

        return obj_org == getattr(request, 'organization', None)
