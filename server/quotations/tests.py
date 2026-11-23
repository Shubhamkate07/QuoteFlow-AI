import datetime
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import Organization, OrganizationMembership, OrganizationRole
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier, SupplierCategory, SupplierStatus
from quotations.models import Quotation, QuotationItem, QuotationStatus, ItemMatchType

User = get_user_model()


class QuotationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="procurement@acme.com", password="Password123!")
        self.org1 = Organization.objects.create(name="Acme Aerospace", slug="acme-aerospace", created_by=self.user)
        self.org2 = Organization.objects.create(name="Beta Robotics", slug="beta-robotics", created_by=self.user)

        # RFQ in Org 1
        self.rfq1 = RFQ.objects.create(
            organization=self.org1,
            rfq_number="RFQ-2026-001",
            title="Titanium Flanges & Fasteners",
            status=RFQStatus.OPEN,
            currency="USD",
            created_by=self.user,
        )
        self.rfq1_item1 = RFQItem.objects.create(
            rfq=self.rfq1,
            position=1,
            item_name="Titanium Hex Flange Bolt M10",
            quantity=Decimal("500.0000"),
            unit="PCS",
            target_unit_price=Decimal("12.50"),
        )
        self.rfq1_item2 = RFQItem.objects.create(
            rfq=self.rfq1,
            position=2,
            item_name="High-Pressure O-Ring Gasket",
            quantity=Decimal("100.0000"),
            unit="PCS",
            target_unit_price=Decimal("4.00"),
        )

        # Supplier in Org 1
        self.supplier1 = Supplier.objects.create(
            organization=self.org1,
            company_name="Titan Precision Fasteners Inc",
            contact_person="Elena Rostova",
            email="elena@titanfasteners.com",
            country="US",
            category=SupplierCategory.FASTENERS,
            status=SupplierStatus.ACTIVE,
            created_by=self.user,
        )

        # Supplier & RFQ in Org 2 (for cross-tenant checks)
        self.rfq2 = RFQ.objects.create(
            organization=self.org2,
            rfq_number="RFQ-BETA-099",
            title="Actuator Motors",
            created_by=self.user,
        )
        self.supplier2 = Supplier.objects.create(
            organization=self.org2,
            company_name="Beta Motors Gmbh",
            contact_person="Hans Schmidt",
            email="hans@betamotors.de",
            country="DE",
            category=SupplierCategory.ELECTRONICS,
            created_by=self.user,
        )

    def test_quotation_creation_and_attributes(self):
        """Test creating a valid quotation with commercial terms and dates."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="TPF-QT-2026-881",
            quotation_date=datetime.date(2026, 11, 20),
            validity_date=datetime.date(2026, 12, 31),
            currency="USD",
            status=QuotationStatus.RECEIVED,
            delivery_terms="FOB Long Beach Port",
            payment_terms="Net 45 Days",
            warranty_information="24 months manufacturer defect coverage",
            lead_time_weeks=Decimal("4.5"),
            created_by=self.user,
        )

        self.assertEqual(quote.organization, self.org1)
        self.assertEqual(quote.rfq, self.rfq1)
        self.assertEqual(quote.supplier, self.supplier1)
        self.assertEqual(quote.quotation_number, "TPF-QT-2026-881")
        self.assertEqual(quote.status, QuotationStatus.RECEIVED)
        self.assertFalse(quote.is_expired)
        self.assertIn("TPF-QT-2026-881", str(quote))

    def test_quotation_line_items_and_divergent_items(self):
        """
        Verify line items:
        1. Exact match to RFQ item.
        2. Substitute item mapped to an RFQ item.
        3. Additional auxiliary item (tooling/freight) with rfq_item=None.
        """
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="TPF-QT-2026-882",
            currency="USD",
        )

        item1 = QuotationItem.objects.create(
            quotation=quote,
            rfq_item=self.rfq1_item1,
            match_type=ItemMatchType.EXACT,
            position=1,
            description="Titanium Hex Flange Bolt M10x1.5 GR5 Ti-6Al-4V",
            manufacturer="Titan Precision",
            model="TI-M10-FLG",
            quantity=Decimal("500.0000"),
            unit="PCS",
            unit_price=Decimal("11.8000"),
            discount=Decimal("100.00"),
            tax=Decimal("464.00"),
            specifications={"grade": "Grade 5 (Ti-6Al-4V)", "tensile_strength": "950 MPa"},
            lead_time_days=28,
        )
        self.assertEqual(item1.line_total, Decimal("6264.00"))

        item2 = QuotationItem.objects.create(
            quotation=quote,
            rfq_item=self.rfq1_item2,
            match_type=ItemMatchType.SUBSTITUTE,
            position=2,
            description="Fluorosilicone Extreme High-Pressure O-Ring (Alternative Spec)",
            manufacturer="Parker Hannifin",
            model="FVMQ-70-ORING",
            quantity=Decimal("100.0000"),
            unit="PCS",
            unit_price=Decimal("4.5000"),
            discount=Decimal("0.00"),
            tax=Decimal("36.00"),
            specifications={"material": "Fluorosilicone FVMQ", "hardness": "70 Shore A"},
            notes="Offers superior temperature resistance up to 200C.",
        )
        self.assertEqual(item2.line_total, Decimal("486.00"))

        item3 = QuotationItem.objects.create(
            quotation=quote,
            rfq_item=None,
            match_type=ItemMatchType.ADDITIONAL,
            position=3,
            description="CNC Lathe Fixturing & Custom Tooling Setup Charge",
            quantity=Decimal("1.0000"),
            unit="LOT",
            unit_price=Decimal("750.0000"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            notes="One-time non-recurring engineering (NRE) charge.",
        )
        self.assertEqual(item3.line_total, Decimal("750.00"))

        quote.recalculate_totals(save=True)
        quote.refresh_from_db()
        self.assertEqual(quote.subtotal, Decimal("7000.00"))
        self.assertEqual(quote.tax_amount, Decimal("500.00"))
        self.assertEqual(quote.total_amount, Decimal("7500.00"))

    def test_validity_date_before_quote_date_raises_validation_error(self):
        """Clean method should forbid validity date prior to quotation date."""
        quote = Quotation(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="INVALID-DATES-01",
            quotation_date=datetime.date(2026, 11, 20),
            validity_date=datetime.date(2026, 11, 10),
        )
        with self.assertRaises(ValidationError) as ctx:
            quote.full_clean()
        self.assertIn('validity_date', ctx.exception.message_dict)

    def test_cross_tenant_rfq_isolation(self):
        """A quotation in Org 1 cannot reference an RFQ belonging to Org 2."""
        quote = Quotation(
            organization=self.org1,
            rfq=self.rfq2,
            supplier=self.supplier1,
            quotation_number="CROSS-TENANT-RFQ",
        )
        with self.assertRaises(ValidationError) as ctx:
            quote.full_clean()
        self.assertIn('rfq', ctx.exception.message_dict)

    def test_cross_tenant_supplier_isolation(self):
        """A quotation in Org 1 cannot reference a Supplier belonging to Org 2."""
        quote = Quotation(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier2,
            quotation_number="CROSS-TENANT-SUP",
        )
        with self.assertRaises(ValidationError) as ctx:
            quote.full_clean()
        self.assertIn('supplier', ctx.exception.message_dict)

    def test_item_mismatched_rfq_validation(self):
        """A QuotationItem cannot link to an RFQItem belonging to a different RFQ."""
        rfq2_item = RFQItem.objects.create(
            rfq=self.rfq2,
            position=1,
            item_name="Brushless DC Motor",
            quantity=Decimal("10.0000"),
            unit="PCS",
        )

        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="MISMATCH-TEST",
        )

        item = QuotationItem(
            quotation=quote,
            rfq_item=rfq2_item,
            description="Mismatched item",
            quantity=Decimal("1.0000"),
            unit="PCS",
            unit_price=Decimal("10.0000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn('rfq_item', ctx.exception.message_dict)

    def test_unique_quotation_number_per_rfq_supplier(self):
        """Cannot insert duplicate quotation number for the same RFQ and Supplier."""
        Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-DUP-TEST",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Quotation.objects.create(
                    organization=self.org1,
                    rfq=self.rfq1,
                    supplier=self.supplier1,
                    quotation_number="QT-DUP-TEST",
                )

    def test_item_quantity_must_be_greater_than_zero(self):
        """Database constraint should reject item quantity <= 0."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-ZERO-QTY",
        )

        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                item = QuotationItem(
                    quotation=quote,
                    description="Zero qty item",
                    quantity=Decimal("0.0000"),
                    unit="PCS",
                    unit_price=Decimal("10.0000"),
                )
                item.full_clean()
                item.save()


class QuotationAPITests(APITestCase):
    def setUp(self):
        # Users
        self.user_org1 = User.objects.create_user(email="buyer1@acme.com", password="Password123!")
        self.user_org2 = User.objects.create_user(email="buyer2@beta.com", password="Password123!")

        # Organizations
        self.org1 = Organization.objects.create(name="Acme Procurement", slug="acme-proc", created_by=self.user_org1)
        self.org2 = Organization.objects.create(name="Beta Robotics", slug="beta-robotics", created_by=self.user_org2)

        # Memberships
        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.user_org1,
            role=OrganizationRole.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.user_org2,
            role=OrganizationRole.OWNER,
            is_active=True,
        )

        # RFQ & Supplier in Org 1
        self.rfq1 = RFQ.objects.create(
            organization=self.org1,
            rfq_number="RFQ-2026-101",
            title="Custom Gear Assembly",
            status=RFQStatus.OPEN,
            currency="USD",
            created_by=self.user_org1,
        )
        self.rfq1_item1 = RFQItem.objects.create(
            rfq=self.rfq1,
            position=1,
            item_name="Spur Gear Module 2.5",
            quantity=Decimal("200.0000"),
            unit="PCS",
            target_unit_price=Decimal("45.00"),
        )
        self.supplier1 = Supplier.objects.create(
            organization=self.org1,
            company_name="Apex Gearworks Corp",
            contact_person="Marcus Vance",
            email="mvance@apexgear.com",
            country="US",
            category=SupplierCategory.MACHINING,
            status=SupplierStatus.ACTIVE,
            created_by=self.user_org1,
        )

        # RFQ & Supplier in Org 2 (cross-tenant target)
        self.rfq2 = RFQ.objects.create(
            organization=self.org2,
            rfq_number="RFQ-BETA-202",
            title="Carbon Fiber Panels",
            status=RFQStatus.OPEN,
            currency="EUR",
            created_by=self.user_org2,
        )
        self.supplier2 = Supplier.objects.create(
            organization=self.org2,
            company_name="EuroComp Gmbh",
            contact_person="Klaus Richter",
            email="k.richter@eurocomp.de",
            country="DE",
            category=SupplierCategory.RAW_MATERIALS,
            status=SupplierStatus.ACTIVE,
            created_by=self.user_org2,
        )

        # JWT Auth for user_org1
        refresh = RefreshToken.for_user(self.user_org1)
        self.token_org1 = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_org1}")

    def test_create_quotation_success(self):
        """User can create a quotation for an RFQ with valid supplier and items."""
        url = "/api/quotations/"
        payload = {
            "rfq_id": str(self.rfq1.id),
            "supplier_id": str(self.supplier1.id),
            "quotation_number": "APEX-QT-9912",
            "quotation_date": "2026-11-20",
            "validity_date": "2026-12-20",
            "currency": "USD",
            "delivery_terms": "DDP Austin Facility",
            "payment_terms": "Net 30 Days",
            "warranty_information": "12 months standard warranty",
            "lead_time_weeks": "3.5",
            "notes": "Includes free initial inspection report.",
            "items": [
                {
                    "rfq_item_id": str(self.rfq1_item1.id),
                    "match_type": "exact",
                    "position": 1,
                    "description": "Precision Spur Gear Module 2.5 40T",
                    "manufacturer": "Apex Gearworks",
                    "model": "AG-SG-25-40",
                    "quantity": "200.0000",
                    "unit": "PCS",
                    "unit_price": "42.5000",
                    "discount": "200.00",
                    "tax": "664.00",
                    "lead_time_days": 21,
                }
            ],
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["quotation_number"], "APEX-QT-9912")
        self.assertEqual(data["supplier_name"], "Apex Gearworks Corp")
        self.assertEqual(data["rfq_number"], "RFQ-2026-101")
        self.assertEqual(len(data["items"]), 1)
        # Check totals: (200 * 42.50 - 200) = 8300 + 664 tax = 8964.00
        self.assertEqual(Decimal(data["subtotal"]), Decimal("8300.00"))
        self.assertEqual(Decimal(data["tax_amount"]), Decimal("664.00"))
        self.assertEqual(Decimal(data["total_amount"]), Decimal("8964.00"))

    def test_list_quotations_for_rfq(self):
        """User can list quotations for an RFQ via query param or nested endpoint."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-LIST-01",
            currency="USD",
        )

        # Method A: /api/quotations/?rfq=<rfq_id>
        resp_a = self.client.get(f"/api/quotations/?rfq={self.rfq1.id}")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        results_a = resp_a.json()
        items_a = results_a.get("results", results_a) if isinstance(results_a, dict) else results_a
        self.assertTrue(any(q["quotation_number"] == "QT-LIST-01" for q in items_a))

        # Method B: /api/rfqs/<rfq_id>/quotations/
        resp_b = self.client.get(f"/api/rfqs/{self.rfq1.id}/quotations/")
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        results_b = resp_b.json()
        self.assertTrue(any(q["quotation_number"] == "QT-LIST-01" for q in results_b))

        # Method C: /api/quotations/rfq/<rfq_id>/
        resp_c = self.client.get(f"/api/quotations/rfq/{self.rfq1.id}/")
        self.assertEqual(resp_c.status_code, status.HTTP_200_OK)

    def test_retrieve_quotation(self):
        """User can retrieve full quotation details by UUID."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-RETRIEVE-01",
            currency="USD",
            delivery_terms="FOB Port",
        )

        response = self.client.get(f"/api/quotations/{quote.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["quotation_number"], "QT-RETRIEVE-01")
        self.assertEqual(data["delivery_terms"], "FOB Port")

    def test_update_quotation_details(self):
        """User can update quotation commercial terms and status."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-UPDATE-01",
            status=QuotationStatus.RECEIVED,
        )

        patch_data = {
            "status": "under_review",
            "payment_terms": "Net 60 Days",
            "notes": "Negotiated 5% discount for bulk payment.",
        }
        response = self.client.patch(f"/api/quotations/{quote.id}/", patch_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "under_review")
        self.assertEqual(data["payment_terms"], "Net 60 Days")

    def test_delete_quotation(self):
        """User can delete a quotation and receive 204 No Content."""
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-DELETE-01",
        )

        response = self.client.delete(f"/api/quotations/{quote.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quotation.objects.filter(pk=quote.id).exists())

    def test_quotation_line_items_crud_and_recalculation(self):
        """
        Verify:
        1. Adding a line item recalculates quotation totals.
        2. Updating a line item updates line_total and recalculates totals.
        3. Deleting a line item recalculates totals.
        """
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-LINE-ITEMS-TEST",
        )

        # 1. Add item
        item_payload = {
            "rfq_item_id": str(self.rfq1_item1.id),
            "match_type": "exact",
            "description": "Spur Gear Module 2.5",
            "quantity": "100.0000",
            "unit": "PCS",
            "unit_price": "50.0000",
            "discount": "0.00",
            "tax": "250.00",
        }
        create_resp = self.client.post(f"/api/quotations/{quote.id}/items/", item_payload, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        item_data = create_resp.json()
        item_id = item_data["id"]
        # Line total = 100 * 50 + 250 = 5250.00
        self.assertEqual(Decimal(item_data["line_total"]), Decimal("5250.00"))

        # Verify parent quote totals recalculated
        quote.refresh_from_db()
        self.assertEqual(quote.subtotal, Decimal("5000.00"))
        self.assertEqual(quote.tax_amount, Decimal("250.00"))
        self.assertEqual(quote.total_amount, Decimal("5250.00"))

        # 2. Update item
        patch_payload = {
            "quantity": "200.0000",  # Double quantity to 200
            "discount": "500.00",     # Add discount
        }
        patch_resp = self.client.patch(f"/api/quotations/{quote.id}/items/{item_id}/", patch_payload, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        # Line total = (200 * 50) - 500 + 250 = 10000 - 500 + 250 = 9750.00
        self.assertEqual(Decimal(patch_resp.json()["line_total"]), Decimal("9750.00"))

        quote.refresh_from_db()
        self.assertEqual(quote.subtotal, Decimal("9500.00"))
        self.assertEqual(quote.total_amount, Decimal("9750.00"))

        # 3. Delete item
        del_resp = self.client.delete(f"/api/quotations/{quote.id}/items/{item_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

        quote.refresh_from_db()
        self.assertEqual(quote.subtotal, Decimal("0.00"))
        self.assertEqual(quote.total_amount, Decimal("0.00"))

    def test_cross_tenant_rfq_blocked(self):
        """User cannot create a quotation linking an RFQ belonging to another organization."""
        payload = {
            "rfq_id": str(self.rfq2.id),  # Belongs to Org 2!
            "supplier_id": str(self.supplier1.id),
            "quotation_number": "CROSS-ORG-RFQ-TEST",
        }
        response = self.client.post("/api/quotations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rfq", response.json())

    def test_cross_tenant_supplier_blocked(self):
        """User cannot create a quotation linking a Supplier belonging to another organization."""
        payload = {
            "rfq_id": str(self.rfq1.id),
            "supplier_id": str(self.supplier2.id),  # Belongs to Org 2!
            "quotation_number": "CROSS-ORG-SUP-TEST",
        }
        response = self.client.post("/api/quotations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("supplier", response.json())

    def test_cross_tenant_quotation_access_denied(self):
        """User in Org 1 cannot view or modify a quotation belonging to Org 2."""
        quote_org2 = Quotation.objects.create(
            organization=self.org2,
            rfq=self.rfq2,
            supplier=self.supplier2,
            quotation_number="ORG2-SECRET-QUOTE",
        )

        response = self.client.get(f"/api/quotations/{quote_org2.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        patch_resp = self.client.patch(f"/api/quotations/{quote_org2.id}/", {"notes": "Hack"})
        self.assertEqual(patch_resp.status_code, status.HTTP_404_NOT_FOUND)

        del_resp = self.client.delete(f"/api/quotations/{quote_org2.id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_mismatched_rfq_item_rejected_on_line_item_creation(self):
        """Adding a line item with an rfq_item_id from a different RFQ is rejected."""
        rfq2_item = RFQItem.objects.create(
            rfq=self.rfq2,
            position=1,
            item_name="Carbon Fiber Plate",
            quantity=Decimal("5.0000"),
            unit="PCS",
        )
        quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="ITEM-MISMATCH-TEST",
        )

        payload = {
            "rfq_item_id": str(rfq2_item.id),  # Belongs to rfq2!
            "description": "Invalid cross RFQ item",
            "quantity": "10.0000",
            "unit_price": "20.0000",
        }
        response = self.client.post(f"/api/quotations/{quote.id}/items/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rfq_item", response.json())


class QuotationDocumentAPITests(APITestCase):
    def setUp(self):
        self.user_org1 = User.objects.create_user(email="doc_buyer@acme.com", password="Password123!")
        self.user_org2 = User.objects.create_user(email="doc_hacker@beta.com", password="Password123!")

        self.org1 = Organization.objects.create(name="Acme Aerospace", slug="acme-aero", created_by=self.user_org1)
        self.org2 = Organization.objects.create(name="Beta Industries", slug="beta-ind", created_by=self.user_org2)

        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.user_org1,
            role=OrganizationRole.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.user_org2,
            role=OrganizationRole.OWNER,
            is_active=True,
        )

        self.rfq1 = RFQ.objects.create(
            organization=self.org1,
            rfq_number="RFQ-DOC-100",
            title="Stainless Fasteners",
            status=RFQStatus.OPEN,
            created_by=self.user_org1,
        )
        self.supplier1 = Supplier.objects.create(
            organization=self.org1,
            company_name="Apex Fasteners Co",
            contact_person="Sam Hill",
            email="sam@apexfasteners.com",
            category=SupplierCategory.FASTENERS,
            created_by=self.user_org1,
        )

        self.quote1 = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq1,
            supplier=self.supplier1,
            quotation_number="QT-DOC-001",
        )

        # JWT Auth
        refresh = RefreshToken.for_user(self.user_org1)
        self.token_org1 = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_org1}")

        # Patch background Celery task dispatch so uploads don't invoke live processing
        from unittest.mock import patch
        self.mock_task_patch = patch('quotations.tasks.process_document_task.delay')
        self.mock_task = self.mock_task_patch.start()
        self.addCleanup(self.mock_task_patch.stop)

        # Byte payloads for tests
        self.pdf_bytes = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        self.png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        self.jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"

        # Generate valid XLSX
        import io, zipfile
        xlsx_buf = io.BytesIO()
        with zipfile.ZipFile(xlsx_buf, 'w') as zf:
            zf.writestr('[Content_Types].xml', '<Types/>')
            zf.writestr('xl/workbook.xml', '<workbook/>')
        self.xlsx_bytes = xlsx_buf.getvalue()

    def test_upload_valid_pdf_via_quotation_documents_endpoint(self):
        """Attaching a valid PDF to an existing quotation stores metadata and generates download url."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("quote_vendor.pdf", self.pdf_bytes, content_type="application/pdf")
        response = self.client.post(
            f"/api/quotations/{self.quote1.id}/documents/",
            {"file": uploaded},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["original_filename"], "quote_vendor.pdf")
        self.assertEqual(data["file_type"], "pdf")
        self.assertEqual(data["file_extension"], "pdf")
        self.assertEqual(data["mime_type"], "application/pdf")
        self.assertEqual(data["processing_status"], "pending")
        self.assertTrue(data["download_url"].endswith(f"/api/quotations/documents/{data['id']}/download/"))

    def test_upload_valid_xlsx_via_quotation_upload_endpoint(self):
        """Creating a new quotation via multipart upload with valid Excel file."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("pricing_sheet.xlsx", self.xlsx_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        payload = {
            "rfq_id": str(self.rfq1.id),
            "supplier_id": str(self.supplier1.id),
            "quotation_number": "EXCEL-QUOTE-889",
            "file": uploaded,
            "currency": "USD",
            "payment_terms": "Net 30",
        }

        response = self.client.post("/api/quotations/upload/", payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["quotation_number"], "EXCEL-QUOTE-889")
        self.assertEqual(len(data["documents"]), 1)
        doc = data["documents"][0]
        self.assertEqual(doc["file_type"], "excel")
        self.assertEqual(doc["original_filename"], "pricing_sheet.xlsx")

    def test_upload_image_png_and_jpg(self):
        """Both PNG and JPG image quotation scans are accepted."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # PNG
        png_file = SimpleUploadedFile("scan_quote.png", self.png_bytes, content_type="image/png")
        resp_png = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": png_file}, format="multipart")
        self.assertEqual(resp_png.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_png.json()["file_type"], "image")

        # JPG
        jpg_file = SimpleUploadedFile("scan_quote.jpg", self.jpg_bytes, content_type="image/jpeg")
        resp_jpg = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": jpg_file}, format="multipart")
        self.assertEqual(resp_jpg.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_jpg.json()["file_type"], "image")

    def test_reject_executable_with_pdf_extension(self):
        """An executable disguised as a PDF (e.g. MZ header) must be rejected."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake_pdf = SimpleUploadedFile("trojan.pdf", b"MZ\x90\x00\x03\x00\x00\x00this is malware", content_type="application/pdf")
        response = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": fake_pdf}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail = str(response.json())
        self.assertTrue("Windows Executable" in detail or "signature" in detail)

    def test_reject_disallowed_extension(self):
        """Files with extensions like .exe, .sh, .bat are rejected immediately."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad_file = SimpleUploadedFile("script.sh", b"#!/bin/bash\necho dangerous", content_type="text/x-sh")
        response = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": bad_file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not permitted", str(response.json()))

    def test_path_traversal_sanitization(self):
        """Path traversal attempts like '../../../../etc/passwd.pdf' are sanitized."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        traversal_file = SimpleUploadedFile("../../../../etc/passwd.pdf", self.pdf_bytes, content_type="application/pdf")
        response = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": traversal_file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["original_filename"], "passwd.pdf")
        # Check that stored disk filename doesn't contain traversal
        doc_id = data["id"]
        from quotations.models import QuotationDocument
        doc = QuotationDocument.objects.get(id=doc_id)
        self.assertNotIn("..", doc.file.name)
        self.assertTrue(doc.file.name.startswith("quotations/documents/"))

    def test_download_document_and_cross_tenant_protection(self):
        """User in Org 1 can download document; User in Org 2 is returned 404."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("secure_contract.pdf", self.pdf_bytes, content_type="application/pdf")
        create_resp = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": uploaded}, format="multipart")
        doc_id = create_resp.json()["id"]

        # 1. Authorized user in Org 1 downloads
        download_resp = self.client.get(f"/api/quotations/documents/{doc_id}/download/")
        self.assertEqual(download_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(download_resp["Content-Type"], "application/pdf")
        self.assertIn("attachment", download_resp["Content-Disposition"])

        # 2. Switch to User in Org 2
        refresh2 = RefreshToken.for_user(self.user_org2)
        token_org2 = str(refresh2.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_org2}")

        hacker_resp = self.client.get(f"/api/quotations/documents/{doc_id}/download/")
        self.assertEqual(hacker_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_document_removes_record_and_file(self):
        """Deleting document deletes DB record and cleans up local storage."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from quotations.models import QuotationDocument

        uploaded = SimpleUploadedFile("to_delete.pdf", self.pdf_bytes, content_type="application/pdf")
        create_resp = self.client.post(f"/api/quotations/{self.quote1.id}/documents/", {"file": uploaded}, format="multipart")
        doc_id = create_resp.json()["id"]

        doc = QuotationDocument.objects.get(id=doc_id)
        file_path = doc.file.path
        import os
        self.assertTrue(os.path.exists(file_path))

        del_resp = self.client.delete(f"/api/quotations/documents/{doc_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(QuotationDocument.objects.filter(id=doc_id).exists())
        self.assertFalse(os.path.exists(file_path))

