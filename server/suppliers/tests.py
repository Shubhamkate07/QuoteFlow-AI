from decimal import Decimal
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import Organization, OrganizationMembership, OrganizationRole
from suppliers.models import Supplier, SupplierCategory, SupplierStatus

User = get_user_model()


class SupplierModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buyer@acme.com", password="Password123!")
        self.org1 = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        self.org2 = Organization.objects.create(name="Beta Industries", slug="beta-ind", created_by=self.user)

        self.supplier = Supplier.objects.create(
            organization=self.org1,
            company_name="Apex Precision Machining Ltd",
            contact_person="Sarah Jenkins",
            email="s.jenkins@apexprecision.com",
            phone="+1 555-019-2834",
            address="1420 Industrial Parkway, Detroit, MI 48201",
            country="US",
            gst_vat_number="US-EIN-94829104",
            website="https://apexprecision.com",
            category=SupplierCategory.MACHINING,
            notes="ISO 9001 certified CNC turning facility.",
            status=SupplierStatus.ACTIVE,
            rating=Decimal("4.85"),
            created_by=self.user,
        )

    def test_supplier_creation_and_attributes(self):
        """Verify supplier attributes, defaults, and relationships."""
        self.assertEqual(self.supplier.organization, self.org1)
        self.assertEqual(self.supplier.company_name, "Apex Precision Machining Ltd")
        self.assertEqual(self.supplier.category, SupplierCategory.MACHINING)
        self.assertEqual(self.supplier.country, "US")
        self.assertEqual(self.supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(self.supplier.rating, Decimal("4.85"))
        self.assertIn("Apex Precision Machining Ltd", str(self.supplier))

    def test_unique_company_name_per_organization(self):
        """
        Verify company name uniqueness within an organization,
        while allowing different organizations to have the same supplier name.
        """
        # Duplicate in Org 1 must raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Supplier.objects.create(
                    organization=self.org1,
                    company_name="Apex Precision Machining Ltd",
                    contact_person="Duplicate Contact",
                    email="duplicate@apex.com",
                )

        # Same company name in Org 2 must succeed
        supplier_org2 = Supplier.objects.create(
            organization=self.org2,
            company_name="Apex Precision Machining Ltd",
            contact_person="Different Contact",
            email="other@apex.com",
        )
        self.assertEqual(supplier_org2.organization, self.org2)


class SupplierAPITests(APITestCase):
    def setUp(self):
        # 1. User & Org A
        self.user_a = User.objects.create_user(
            email="buyer.a@acme.com", password="Password123!", full_name="Buyer A"
        )
        self.org_a = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user_a)
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)

        # 2. User & Org B (Target for isolation testing)
        self.user_b = User.objects.create_user(
            email="buyer.b@globex.com", password="Password123!", full_name="Buyer B"
        )
        self.org_b = Organization.objects.create(name="Globex Corp", slug="globex-corp", created_by=self.user_b)
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        # 3. Create initial supplier for Org A
        self.supplier_a = Supplier.objects.create(
            organization=self.org_a,
            company_name="Apex Machining",
            contact_person="Sarah Jenkins",
            email="sarah@apex.com",
            phone="+1 555-0100",
            address="100 Factory Rd",
            country="US",
            gst_vat_number="US-EIN-12345",
            category=SupplierCategory.MACHINING,
            status=SupplierStatus.ACTIVE,
            created_by=self.user_a,
        )

    def test_api_list_suppliers_scoped_to_organization(self):
        """Verify list endpoint returns only suppliers belonging to caller's active organization."""
        # Create a supplier for Org B
        Supplier.objects.create(
            organization=self.org_b,
            company_name="Globex Secret Vendor",
            contact_person="Hank Scorpio",
            email="hank@globex.com",
            created_by=self.user_b,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.get("/api/suppliers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['company_name'], "Apex Machining")

    def test_api_search_and_filter_suppliers(self):
        """Verify searching and filtering by category, country, status."""
        Supplier.objects.create(
            organization=self.org_a,
            company_name="Shenzhen Fasteners Co.",
            contact_person="Li Wei",
            email="li@szfasteners.cn",
            country="CN",
            category=SupplierCategory.FASTENERS,
            status=SupplierStatus.ACTIVE,
            created_by=self.user_a,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )

        # Search for 'Shenzhen'
        res_search = self.client.get("/api/suppliers/?search=Shenzhen")
        data_search = res_search.data['results'] if 'results' in res_search.data else res_search.data
        self.assertEqual(len(data_search), 1)
        self.assertEqual(data_search[0]['company_name'], "Shenzhen Fasteners Co.")

        # Filter by category 'fasteners'
        res_cat = self.client.get("/api/suppliers/?category=fasteners")
        data_cat = res_cat.data['results'] if 'results' in res_cat.data else res_cat.data
        self.assertEqual(len(data_cat), 1)
        self.assertEqual(data_cat[0]['category'], "fasteners")

        # Filter by country 'CN'
        res_country = self.client.get("/api/suppliers/?country=CN")
        data_country = res_country.data['results'] if 'results' in res_country.data else res_country.data
        self.assertEqual(len(data_country), 1)
        self.assertEqual(data_country[0]['country'], "CN")

    def test_api_create_supplier(self):
        """Verify creating a new supplier with validation."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        payload = {
            "company_name": "Titanium Dynamics GmbH",
            "contact_person": "Hans Gruber",
            "email": "h.gruber@titaniumdyn.de",
            "phone": "+49 89 123456",
            "address": "Industriestrasse 42, Munich",
            "country": "DE",
            "gst_vat_number": "DE998877665",
            "website": "https://titaniumdyn.de",
            "category": "raw_materials",
            "notes": "Medical grade titanium bar stock supplier",
            "status": "active",
            "rating": "4.90",
        }
        response = self.client.post("/api/suppliers/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['company_name'], "Titanium Dynamics GmbH")
        self.assertEqual(response.data['country'], "DE")
        self.assertEqual(response.data['category'], "raw_materials")
        self.assertEqual(response.data['rating'], "4.90")

    def test_api_retrieve_supplier(self):
        """Verify retrieving supplier detail."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.get(f"/api/suppliers/{self.supplier_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], "Apex Machining")

    def test_api_update_supplier(self):
        """Verify updating supplier fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        payload = {
            "phone": "+1 555-9999",
            "rating": "4.95",
        }
        response = self.client.patch(f"/api/suppliers/{self.supplier_a.id}/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], "+1 555-9999")
        self.assertEqual(response.data['rating'], "4.95")

    def test_api_delete_supplier(self):
        """Verify deleting a supplier returns 204 No Content."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.delete(f"/api/suppliers/{self.supplier_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Supplier.objects.filter(id=self.supplier_a.id).exists())

    def test_cross_organization_supplier_access_prevented(self):
        """
        SECURITY TEST: Verify that User B from Org B CANNOT retrieve, update,
        or delete a supplier belonging to Org A, and cannot spoof organization headers.
        """
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
            HTTP_X_ORGANIZATION_ID=str(self.org_b.id),
        )

        # Retrieve Org A's supplier as User B
        res_get = self.client.get(f"/api/suppliers/{self.supplier_a.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # Update Org A's supplier as User B
        res_patch = self.client.patch(
            f"/api/suppliers/{self.supplier_a.id}/", {"company_name": "Hacked Name"}, format='json'
        )
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        # Delete Org A's supplier as User B
        res_del = self.client.delete(f"/api/suppliers/{self.supplier_a.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)

        # User B attempts to spoof X-Organization-Id with Org A's ID
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        res_spoof = self.client.get("/api/suppliers/")
        self.assertEqual(res_spoof.status_code, status.HTTP_403_FORBIDDEN)
