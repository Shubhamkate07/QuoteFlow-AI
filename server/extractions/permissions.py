"""
Permissions for AI Quotation Extraction Review and Approval workflows.
Enforces multi-tier role-based access control (RBAC) within tenant organizations.
"""

from rest_framework.permissions import BasePermission
from organizations.models import OrganizationRole, OrganizationMembership


def get_user_org_membership(user, organization):
    """Safely retrieves active organization membership for user and tenant."""
    if not user or not user.is_authenticated or not organization:
        return None
    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()


class CanViewQuotationExtraction(BasePermission):
    """Allows active members of an organization to view extractions."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, 'organization', None)
        membership = get_user_org_membership(request.user, org)
        return membership is not None


class CanReviewQuotationExtraction(BasePermission):
    """
    Allows procurement users, procurement managers, admins, and owners
    to edit, correct, and mark fields as reviewed.
    """
    ALLOWED_ROLES = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.PROCUREMENT_MANAGER,
        OrganizationRole.PROCUREMENT_USER,
    }

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, 'organization', None)
        membership = get_user_org_membership(request.user, org)
        if not membership:
            return False
        return membership.role in self.ALLOWED_ROLES


class CanApproveQuotationExtraction(BasePermission):
    """
    Allows ONLY procurement managers, admins, and owners to formally approve extractions.
    Standard procurement users can make corrections but cannot grant final sign-off.
    """
    ALLOWED_ROLES = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.PROCUREMENT_MANAGER,
    }

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, 'organization', None)
        membership = get_user_org_membership(request.user, org)
        if not membership:
            return False
        return membership.role in self.ALLOWED_ROLES
