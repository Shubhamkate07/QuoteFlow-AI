import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models import BaseModel


class OrganizationRole(models.TextChoices):
    OWNER = 'owner', 'Owner'
    ADMIN = 'admin', 'Admin'
    PROCUREMENT_MANAGER = 'procurement_manager', 'Procurement Manager'
    PROCUREMENT_USER = 'procurement_user', 'Procurement User'


class Organization(BaseModel):
    """
    Represents a company or tenant workspace in QuoteFlow AI.
    All procurement resources (RFQs, quotations, suppliers) belong to an Organization.
    """
    name = models.CharField(max_length=255, help_text="Company or Workspace Name")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, help_text="URL-friendly identifier")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_organizations',
    )
    is_active = models.BooleanField(default=True, help_text="Deactivated organizations block access for all members")
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Organization-wide preferences (default currency, timezone, risk weights)",
    )

    class Meta:
        verbose_name = 'organization'
        verbose_name_plural = 'organizations'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def owner(self):
        """Returns the primary owner user of this organization."""
        owner_membership = self.memberships.filter(role=OrganizationRole.OWNER, is_active=True).first()
        return owner_membership.user if owner_membership else None


class OrganizationMembership(BaseModel):
    """
    Through model associating a User with an Organization under an assigned Role.
    Supports users belonging to multiple organizations with differing permission levels.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
    )
    role = models.CharField(
        max_length=32,
        choices=OrganizationRole.choices,
        default=OrganizationRole.PROCUREMENT_USER,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Allows suspending user access within this tenant without deleting history",
    )

    class Meta:
        verbose_name = 'organization membership'
        verbose_name_plural = 'organization memberships'
        constraints = [
            models.UniqueConstraint(fields=['organization', 'user'], name='unique_org_user_membership'),
        ]
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['user', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.organization.name} ({self.get_role_display()})"


class InvitationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    EXPIRED = 'expired', 'Expired'
    REVOKED = 'revoked', 'Revoked'


class OrganizationInvitation(BaseModel):
    """
    Future-ready model for inviting team members to an organization with a pre-assigned role.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=32,
        choices=OrganizationRole.choices,
        default=OrganizationRole.PROCUREMENT_USER,
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'organization invitation'
        verbose_name_plural = 'organization invitations'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'email'],
                condition=models.Q(status=InvitationStatus.PENDING),
                name='unique_pending_org_invitation',
            ),
        ]

    def __str__(self):
        return f"Invite {self.email} to {self.organization.name} as {self.get_role_display()}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
