from rest_framework.permissions import BasePermission
from organizations.models import OrganizationRole, OrganizationMembership


class IsOrganizationMember(BasePermission):
    """
    Allows access only to active members of the organization in request context.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if organization is attached to request (e.g. via middleware or view kwargs)
        organization = getattr(request, 'organization', None)
        if not organization:
            return True  # Let view or object-level permission resolve if org is not on request
        
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True,
        ).exists()

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verify object belongs to the tenant and user has access
        obj_org = getattr(obj, 'organization', None)
        if not obj_org:
            return True
        
        return OrganizationMembership.objects.filter(
            organization=obj_org,
            user=request.user,
            is_active=True,
        ).exists()


class HasOrganizationRole(BasePermission):
    """
    Dynamic permission to check whether the requesting user has one of the required roles.
    Usage: permission_classes = [HasOrganizationRole([OrganizationRole.OWNER, OrganizationRole.ADMIN])]
    """
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        organization = getattr(request, 'organization', None)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            role__in=self.allowed_roles,
            is_active=True,
        ).exists()


class IsOrganizationOwner(BasePermission):
    def has_permission(self, request, view):
        organization = getattr(request, 'organization', None)
        if not organization or not request.user.is_authenticated:
            return False
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            role=OrganizationRole.OWNER,
            is_active=True,
        ).exists()


class IsOrganizationAdmin(BasePermission):
    """Allows Owner and Admin roles."""
    def has_permission(self, request, view):
        organization = getattr(request, 'organization', None)
        if not organization or not request.user.is_authenticated:
            return False
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            role__in=[OrganizationRole.OWNER, OrganizationRole.ADMIN],
            is_active=True,
        ).exists()


class IsProcurementManager(BasePermission):
    """Allows Owner, Admin, and Procurement Manager roles."""
    def has_permission(self, request, view):
        organization = getattr(request, 'organization', None)
        if not organization or not request.user.is_authenticated:
            return False
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            role__in=[
                OrganizationRole.OWNER,
                OrganizationRole.ADMIN,
                OrganizationRole.PROCUREMENT_MANAGER,
            ],
            is_active=True,
        ).exists()
