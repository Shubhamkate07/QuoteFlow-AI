from decimal import Decimal
from datetime import date, timedelta
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import Organization, OrganizationMembership, OrganizationRole
from rfqs.models import (
    RFQ,
    RFQItem,
    RFQItemSpecification,
    RFQStatus,
    SpecificationImportance,
)

User = get_user_model()


class RFQModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buyer@acme.com", password="SecurePassword123!")
        self.org1 = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        self.org2 = Organization.objects.create(name="Beta Industries", slug="beta-ind", created_by=self.user)

        self.rfq = RFQ.objects.create(
            organization=self.org1,
            rfq_number="RFQ-2026-001",
            title="CNC Machined Aluminum Housings",
            description="Precision parts for robotics assembly",
            status=RFQStatus.DRAFT,
            required_delivery_date=date.today() + timedelta(days=30),
            currency="USD",
            notes="Requires material test reports",
            created_by=self.user,
        )

    def test_rfq_creation_and_attributes(self):
        """Verify RFQ is correctly linked to the organization and defaults work."""
        self.assertEqual(self.rfq.organization, self.org1)
        self.assertEqual(self.rfq.rfq_number, "RFQ-2026-001")
        self.assertEqual(self.rfq.status, RFQStatus.DRAFT)
        self.assertEqual(self.rfq.currency, "USD")
        self.assertIn("RFQ-2026-001", str(self.rfq))

    def test_unique_rfq_number_per_organization(self):
        """
        Verify that RFQ numbers are unique per organization,
        but different organizations can use the same RFQ number.
        """
        from django.db import transaction

        # Duplicate in same org must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RFQ.objects.create(
                    organization=self.org1,
                    rfq_number="RFQ-2026-001",
                    title="Duplicate RFQ",
                )

        # Same RFQ number in different org must succeed
        rfq_org2 = RFQ.objects.create(
            organization=self.org2,
            rfq_number="RFQ-2026-001",
            title="Org 2 RFQ with same number",
        )
        self.assertEqual(rfq_org2.organization, self.org2)

    def test_rfq_item_creation_with_specifications(self):
        """Verify RFQ item creation, BOM relationships, and flexible specifications."""
        item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Aluminum 6061-T6 Housing",
            description="Anodized black enclosure",
            quantity=Decimal("500.0000"),
            unit="PCS",
            target_unit_price=Decimal("45.50"),
            manufacturer_preference="Haas or Mazak milled",
            custom_specifications={
                "surface_finish": "Ra 0.8 µm",
                "coating": "MIL-A-8625 Type III Hardcoat",
                "cad_drawing_ref": "DWG-ROB-2026-A1",
            },
        )

        self.assertEqual(item.rfq, self.rfq)
        self.assertEqual(item.quantity, Decimal("500.0000"))
        self.assertEqual(item.custom_specifications["surface_finish"], "Ra 0.8 µm")
        self.assertEqual(self.rfq.items.count(), 1)

        spec1 = RFQItemSpecification.objects.create(
            item=item,
            parameter_name="Material Grade",
            required_value="Aluminum 6061-T6",
            tolerance_or_unit="ASTM B221",
            importance=SpecificationImportance.MANDATORY,
        )

        spec2 = RFQItemSpecification.objects.create(
            item=item,
            parameter_name="Dimensional Tolerance",
            required_value="±0.05",
            tolerance_or_unit="mm",
            importance=SpecificationImportance.MANDATORY,
        )

        self.assertEqual(item.specifications.count(), 2)
        self.assertIn("Material Grade", str(spec1))
        self.assertEqual(spec1.importance, SpecificationImportance.MANDATORY)

    def test_rfq_item_quantity_validation(self):
        """Verify check constraint prevents zero or negative quantities."""
        from django.db import transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RFQItem.objects.create(
                    rfq=self.rfq,
                    position=2,
                    item_name="Zero Quantity Item",
                    quantity=Decimal("0.0000"),
                    unit="PCS",
                )

    def test_cascade_deletion(self):
        """Verify deleting an RFQ cascades to items and their specifications."""
        item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Test Widget",
            quantity=Decimal("10.0"),
            unit="PCS",
        )
        RFQItemSpecification.objects.create(
            item=item,
            parameter_name="Color",
            required_value="Matte Black",
        )

        rfq_id = self.rfq.id
        item_id = item.id

        self.rfq.delete()

        self.assertFalse(RFQ.objects.filter(id=rfq_id).exists())
        self.assertFalse(RFQItem.objects.filter(id=item_id).exists())
        self.assertEqual(RFQItemSpecification.objects.count(), 0)


class RFQAPITests(APITestCase):
    def setUp(self):
        # 1. Setup User and Org A
        self.user_a = User.objects.create_user(email="buyer.a@acmecorp.com", password="Password123!", full_name="Buyer A")
        self.org_a = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user_a)
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)

        # 2. Setup User and Org B (Tenant Isolation Test Target)
        self.user_b = User.objects.create_user(email="buyer.b@globex.com", password="Password123!", full_name="Buyer B")
        self.org_b = Organization.objects.create(name="Globex Corp", slug="globex-corp", created_by=self.user_b)
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        # 3. Create an initial RFQ for Org A
        self.rfq_a = RFQ.objects.create(
            organization=self.org_a,
            rfq_number="RFQ-2026-001",
            title="Custom Steel Shafts",
            description="Precision milled shafts",
            status=RFQStatus.DRAFT,
            currency="USD",
            created_by=self.user_a,
        )
        self.item_a = RFQItem.objects.create(
            rfq=self.rfq_a,
            position=1,
            item_name="Drive Shaft 25mm",
            quantity=Decimal("200.0"),
            unit="PCS",
        )

    def test_api_list_rfqs_scoped_to_organization(self):
        """Verify list endpoint returns only RFQs belonging to the caller's active organization."""
        # Create an RFQ for Org B
        RFQ.objects.create(
            organization=self.org_b,
            rfq_number="RFQ-2026-999",
            title="Globex Secret Project",
            created_by=self.user_b,
        )

        # User A requests their RFQs
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.get("/api/rfqs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Results can be direct array or paginated results object
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['rfq_number'], "RFQ-2026-001")
        self.assertEqual(data[0]['title'], "Custom Steel Shafts")

    def test_api_search_and_filter_rfqs(self):
        """Verify search query parameter and status filter work correctly."""
        RFQ.objects.create(
            organization=self.org_a,
            rfq_number="RFQ-2026-002",
            title="Electronic PCB Assembly",
            status=RFQStatus.OPEN,
            currency="USD",
            created_by=self.user_a,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )

        # Search for 'PCB'
        res_search = self.client.get("/api/rfqs/?search=PCB")
        data_search = res_search.data['results'] if 'results' in res_search.data else res_search.data
        self.assertEqual(len(data_search), 1)
        self.assertEqual(data_search[0]['title'], "Electronic PCB Assembly")

        # Filter by status 'open'
        res_filter = self.client.get("/api/rfqs/?status=open")
        data_filter = res_filter.data['results'] if 'results' in res_filter.data else res_filter.data
        self.assertEqual(len(data_filter), 1)
        self.assertEqual(data_filter[0]['status'], "open")

    def test_api_create_rfq_with_items_and_specifications(self):
        """Verify creating an RFQ with nested BOM items and technical specifications in one atomic call."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )

        payload = {
            "title": "Industrial Titanium Valves",
            "description": "High pressure chemical valves",
            "status": "draft",
            "currency": "EUR",
            "required_delivery_date": str(date.today() + timedelta(days=45)),
            "items": [
                {
                    "item_name": "Titanium Ball Valve 2-inch",
                    "quantity": "50.0",
                    "unit": "PCS",
                    "target_unit_price": "240.00",
                    "manufacturer_preference": "Swagelok",
                    "custom_specifications": {"ansi_class": 600},
                    "specifications": [
                        {
                            "parameter_name": "Pressure Rating",
                            "required_value": "600 PSI",
                            "tolerance_or_unit": "PSI",
                            "importance": "mandatory",
                        },
                        {
                            "parameter_name": "Body Material",
                            "required_value": "Grade 2 Titanium",
                            "importance": "mandatory",
                        }
                    ]
                }
            ]
        }

        response = self.client.post("/api/rfqs/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("rfq_number", response.data)
        self.assertEqual(response.data['title'], "Industrial Titanium Valves")
        self.assertEqual(response.data['currency'], "EUR")
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(len(response.data['items'][0]['specifications']), 2)
        spec_names = [s['parameter_name'] for s in response.data['items'][0]['specifications']]
        self.assertIn("Pressure Rating", spec_names)
        self.assertIn("Body Material", spec_names)

    def test_api_retrieve_rfq_detail(self):
        """Verify retrieving full RFQ details including nested line items."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.get(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Custom Steel Shafts")
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['item_name'], "Drive Shaft 25mm")

    def test_api_update_rfq(self):
        """Verify updating RFQ status and fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        payload = {
            "title": "Custom Steel Shafts - Updated",
            "status": "open",
        }
        response = self.client.patch(f"/api/rfqs/{self.rfq_a.id}/", payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Custom Steel Shafts - Updated")
        self.assertEqual(response.data['status'], "open")

    def test_api_delete_rfq(self):
        """Verify deleting an RFQ returns 204 No Content."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        response = self.client.delete(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RFQ.objects.filter(id=self.rfq_a.id).exists())

    def test_api_rfq_item_crud_endpoints(self):
        """Verify nested RFQ line item endpoints: create, list, update, and delete."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )

        # 1. Add item
        item_payload = {
            "item_name": "Precision Bearing 608RS",
            "quantity": "1000.0",
            "unit": "PCS",
            "target_unit_price": "2.50",
            "specifications": [
                {
                    "parameter_name": "ABEC Rating",
                    "required_value": "ABEC 7",
                    "importance": "mandatory",
                }
            ]
        }
        create_res = self.client.post(f"/api/rfqs/{self.rfq_a.id}/items/", item_payload, format='json')
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        item_id = create_res.data['id']
        self.assertEqual(create_res.data['item_name'], "Precision Bearing 608RS")
        self.assertEqual(len(create_res.data['specifications']), 1)

        # 2. List items
        list_res = self.client.get(f"/api/rfqs/{self.rfq_a.id}/items/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 2)  # item_a + new bearing item

        # 3. Update item
        patch_res = self.client.patch(
            f"/api/rfqs/{self.rfq_a.id}/items/{item_id}/",
            {"quantity": "1500.0"},
            format='json',
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data['quantity'], "1500.0000")

        # 4. Delete item
        del_res = self.client.delete(f"/api/rfqs/{self.rfq_a.id}/items/{item_id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RFQItem.objects.filter(id=item_id).exists())

    def test_cross_organization_rfq_access_prevented(self):
        """
        SECURITY TEST: Verify that User B from Org B CANNOT retrieve, update,
        or delete an RFQ belonging to Org A, even if they know the UUID.
        """
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
            HTTP_X_ORGANIZATION_ID=str(self.org_b.id),
        )

        # Retrieve Org A's RFQ as User B
        res_get = self.client.get(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # Update Org A's RFQ as User B
        res_patch = self.client.patch(f"/api/rfqs/{self.rfq_a.id}/", {"title": "Hacked Title"}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        # Delete Org A's RFQ as User B
        res_del = self.client.delete(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)

        # User B attempts to spoof X-Organization-Id with Org A's ID
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_b}",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        res_spoof = self.client.get("/api/rfqs/")
        self.assertEqual(res_spoof.status_code, status.HTTP_403_FORBIDDEN)
