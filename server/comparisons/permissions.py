"""
Permissions for Quotation Comparisons and Multi-Factor Evaluations.
Guarantees tenant isolation and organization scoping for all comparison APIs.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from organizations.selectors import get_active_organization_for_request
from organizations.models import OrganizationMembership, OrganizationRole


class IsComparisonOrganizationMember(BasePermission):
    """
    Guarantees the requesting user belongs to the active organization
    and has authorization for comparison operations and weight modifications.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            organization = getattr(request, 'organization', None) or get_active_organization_for_request(request)
            request.organization = organization
        except Exception:
            return False

        if not organization:
            return False

        # Read-only actions permitted for any active member
        if request.method in SAFE_METHODS:
            return True

        # Mutation actions (generate, regenerate, update weights)
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True,
        ).exists()

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        obj_org = getattr(obj, 'organization', None)
        if not obj_org and hasattr(obj, 'rfq'):
            obj_org = obj.rfq.organization
        if not obj_org and hasattr(obj, 'document'):
            obj_org = obj.document.organization

        req_org = getattr(request, 'organization', None)
        return obj_org == req_org
