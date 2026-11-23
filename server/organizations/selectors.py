"""
Selectors for organizations, workspaces, and memberships.
Provides safe tenant resolution for multi-tenant requests.
"""

from rest_framework.exceptions import PermissionDenied
from organizations.models import Organization, OrganizationMembership


def get_user_organizations(*, user):
    """Returns all active organizations for the user."""
    return Organization.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        is_active=True,
    ).distinct()


def get_active_organization_for_request(request) -> Organization:
    """
    Resolves and strictly validates the active organization for an authenticated request.
    Never trusts raw client input without verifying active membership.

    1. Checks 'X-Organization-Id' header if present.
    2. Verifies that request.user has an active membership in that organization.
    3. If no header is provided, falls back to the user's primary/first active organization.
    4. Raises PermissionDenied (403) if unauthorized or not an active member.
    """
    if not request.user or not request.user.is_authenticated:
        raise PermissionDenied("Authentication credentials were not provided.")

    org_id = request.headers.get('X-Organization-Id') or request.query_params.get('organization_id')

    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True,
        organization__is_active=True,
    ).select_related('organization')

    if org_id:
        membership = memberships.filter(organization_id=org_id).first()
        if not membership:
            raise PermissionDenied("You do not have access to the specified organization.")
        return membership.organization

    # Fallback to the user's primary organization
    first_membership = memberships.first()
    if not first_membership:
        raise PermissionDenied("You are not an active member of any company organization.")

    return first_membership.organization
