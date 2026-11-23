from django.db import IntegrityError
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from organizations.permissions import (
    IsOrganizationMember,
    IsOrganizationOwner,
    IsOrganizationAdmin,
    IsProcurementManager,
)

User = get_user_model()


class MultiTenantModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='owner@acme.com', password='password123', full_name='Acme Owner')
        self.user2 = User.objects.create_user(email='buyer@acme.com', password='password123', full_name='Acme Buyer')
        self.user3 = User.objects.create_user(email='external@othercorp.com', password='password123', full_name='External User')

        self.org1 = Organization.objects.create(name='Acme Corporation', slug='acme-corp', created_by=self.user1)
        self.org2 = Organization.objects.create(name='Other Corporation', slug='other-corp', created_by=self.user3)

        self.membership_owner = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.user1,
            role=OrganizationRole.OWNER,
        )
        self.membership_buyer = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.user2,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

    def test_organization_owner_resolution(self):
        """Verify the owner property correctly resolves the organization's owner user."""
        self.assertEqual(self.org1.owner, self.user1)
        self.assertIsNone(self.org2.owner)

    def test_unique_membership_constraint(self):
        """Verify a user cannot have duplicate memberships in the same organization."""
        with self.assertRaises(IntegrityError):
            OrganizationMembership.objects.create(
                organization=self.org1,
                user=self.user1,
                role=OrganizationRole.ADMIN,
            )

    def test_multi_organization_membership(self):
        """Verify a single user can belong to multiple organizations with different roles."""
        membership2 = OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.user2,
            role=OrganizationRole.PROCUREMENT_USER,
        )
        self.assertEqual(self.user2.organization_memberships.count(), 2)
        self.assertEqual(self.membership_buyer.role, OrganizationRole.PROCUREMENT_MANAGER)
        self.assertEqual(membership2.role, OrganizationRole.PROCUREMENT_USER)

    def test_tenant_permissions_isolation(self):
        """Verify permission classes enforce organization and role boundaries."""
        factory = RequestFactory()
        
        # Test 1: Active member
        req = factory.get('/')
        req.user = self.user2
        req.organization = self.org1
        self.assertTrue(IsOrganizationMember().has_permission(req, None))
        self.assertTrue(IsProcurementManager().has_permission(req, None))
        self.assertFalse(IsOrganizationOwner().has_permission(req, None))
        self.assertFalse(IsOrganizationAdmin().has_permission(req, None))

        # Test 2: External user attempting access to Org 1
        req_external = factory.get('/')
        req_external.user = self.user3
        req_external.organization = self.org1
        self.assertFalse(IsOrganizationMember().has_permission(req_external, None))
        self.assertFalse(IsProcurementManager().has_permission(req_external, None))
