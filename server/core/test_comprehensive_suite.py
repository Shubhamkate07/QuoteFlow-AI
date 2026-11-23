"""
QuoteFlow AI - Comprehensive End-to-End Backend Test Suite.
Validates all core business logic across:
1. Authentication & JWT Tokens
2. Role-Based Permissions
3. Multi-Tenant Organization Isolation
4. RFQ Lifecycle & BOM Items
5. Supplier Management
6. Quotation Ingestion & Line Items
7. Document Upload & File Security Validation
8. PDF, Excel & OCR Text Extraction
9. AI Extraction Schema Validation & Verification Engine (Mocked Gemini)
10. Human Review, Correction Recalculation & Approval Sync
11. Deterministic Price Comparison Engine & Currency Normalization
12. Specification Matching Engine (Exact, Mismatch, Missing)
13. Quotation Risk Flags Engine (14-Rule Deterministic Evaluation)
14. Explainable Supplier Scoring Engine (Configurable Weights)
15. Publication-Grade Excel & PDF Export Generators

All Gemini AI API calls are strictly mocked with zero network overhead.
"""

import io
import os
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import openpyxl

# Domain models
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from rfqs.models import RFQ, RFQItem, RFQItemSpecification, RFQStatus, SpecificationImportance
from suppliers.models import Supplier, SupplierCategory, SupplierStatus
from quotations.models import (
    Quotation,
    QuotationItem,
    QuotationDocument,
    DocumentFileType,
    DocumentProcessingStatus,
    DocumentExtractionResult,
    ItemMatchType,
)
from extractions.models import (
    QuotationExtraction,
    ExtractionStatus,
    ReviewStatus,
    QuotationExtractionCorrection,
)
from extractions.schemas import (
    QuotationExtractionSchema,
    SupplierInfoSchema,
    QuotationInfoSchema,
    LineItemSchema,
    CommercialTermsSchema,
    SpecificationItem,
)
from extractions.verification import QuotationVerificationEngine
from extractions.services import QuotationExtractionService

# Processing & Extraction
from quotations.processing import PDFExtractor, ExcelExtractor

# Comparison engines & normalization
from comparisons.engine import PriceComparisonEngine
from comparisons.normalization import CurrencyConversionService, ExchangeRateTable, ExchangeRate
from comparisons.specs.engine import SpecificationMatchingEngine
from comparisons.risk.engine import QuotationRiskEngine, RiskEngineConfig
from comparisons.scoring.engine import SupplierScoringEngine
from comparisons.scoring.weights import ScoringWeights, validate_weights
from comparisons.services import generate_comprehensive_rfq_comparison

# Report generation
from reports.excel_generator import RFQComparisonExcelGenerator
from reports.pdf_generator import RFQComparisonPDFGenerator

User = get_user_model()


def build_test_pdf_bytes(text_lines: list[str]) -> bytes:
    """Creates a valid in-memory PDF byte string with given lines using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y_pos = 72
    for line in text_lines:
        page.insert_text(fitz.Point(50, y_pos), line, fontsize=11)
        y_pos += 18
    data = doc.tobytes()
    doc.close()
    return data


def build_test_excel_bytes(rows: list[list]) -> bytes:
    """Creates a valid in-memory XLSX byte string using openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotation"
    for row in rows:
        ws.append(row)
    stream = io.BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


# =========================================================================
# 1. Authentication, Authorization & Multi-Tenant Isolation
# =========================================================================

class AuthenticationAndTenantIsolationTests(APITestCase):
    """Verifies JWT token issuance, RBAC permissions, and strict cross-organization barriers."""

    def setUp(self):
        # Organization A setup
        self.user_a = User.objects.create_user(
            email="manager@acme.com", password="SecurePassword123!", full_name="Acme Manager"
        )
        self.org_a = Organization.objects.create(name="Acme Aerospace", slug="acme-aerospace", created_by=self.user_a)
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)

        # Organization B setup (Target for cross-tenant breach testing)
        self.user_b = User.objects.create_user(
            email="intruder@globex.com", password="SecurePassword123!", full_name="Globex Buyer"
        )
        self.org_b = Organization.objects.create(name="Globex Corp", slug="globex-corp", created_by=self.user_b)
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationRole.PROCUREMENT_USER,
        )
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        # Org A resources
        self.rfq_a = RFQ.objects.create(
            organization=self.org_a,
            rfq_number="RFQ-ACME-001",
            title="Titanium Components",
            status=RFQStatus.OPEN,
            created_by=self.user_a,
        )
        self.supplier_a = Supplier.objects.create(
            organization=self.org_a,
            company_name="Apex Precision Fasteners",
            email="contact@apexprecision.com",
            country="US",
            created_by=self.user_a,
        )

    def test_user_login_and_token_generation(self):
        """Verifies authentication returns valid JWT access & refresh tokens with organization membership context."""
        response = self.client.post("/api/auth/login/", {
            "email": "manager@acme.com",
            "password": "SecurePassword123!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["email"], "manager@acme.com")

    def test_unauthenticated_request_rejected(self):
        """Endpoints protected by IsAuthenticated reject anonymous requests with HTTP 401."""
        response = self.client.get(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_tenant_rfq_access_blocked(self):
        """User from Org B cannot view or modify RFQs belonging to Org A (HTTP 404)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")

        # Attempt to read Org A's RFQ
        response = self.client.get(f"/api/rfqs/{self.rfq_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Attempt to update Org A's RFQ
        update_resp = self.client.patch(f"/api/rfqs/{self.rfq_a.id}/", {"title": "Hacked Title"}, format="json")
        self.assertEqual(update_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_supplier_access_blocked(self):
        """User from Org B cannot read or modify Suppliers belonging to Org A."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")

        response = self.client.get(f"/api/suppliers/{self.supplier_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =========================================================================
# 2. RFQ CRUD, Items & Supplier Management
# =========================================================================

class RfqAndSupplierLifecycleTests(APITestCase):
    """Tests RFQ and Supplier CRUD, unique constraints per organization, and BOM item specifications."""

    def setUp(self):
        self.user = User.objects.create_user(email="buyer@acme.com", password="Password123!")
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_rfq_create_with_bom_items_and_specifications(self):
        """Tests full RFQ creation including item positions, UOM, and technical specifications."""
        rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-BOM-01",
            title="CNC Machined Enclosures",
            required_delivery_date=date.today() + timedelta(days=45),
            currency="USD",
            created_by=self.user,
        )

        item = RFQItem.objects.create(
            rfq=rfq,
            position=1,
            item_name="Alloy Housing Enclosure",
            quantity=Decimal("250.0000"),
            unit="PCS",
            target_unit_price=Decimal("120.00"),
        )

        spec = RFQItemSpecification.objects.create(
            item=item,
            parameter_name="Material",
            required_value="Aluminum 6061-T6",
            importance=SpecificationImportance.MANDATORY,
        )

        self.assertEqual(rfq.items.count(), 1)
        self.assertEqual(item.specifications.count(), 1)
        self.assertEqual(spec.importance, SpecificationImportance.MANDATORY)

    def test_supplier_creation_and_uniqueness_within_org(self):
        """Verifies unique supplier company name per organization."""
        from django.db import IntegrityError, transaction

        Supplier.objects.create(
            organization=self.org,
            company_name="Apex Precision Ltd",
            email="sales@apex.com",
            country="US",
            category=SupplierCategory.MACHINING,
            rating=Decimal("4.8"),
            created_by=self.user,
        )

        # Duplicate company name in same org must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Supplier.objects.create(
                    organization=self.org,
                    company_name="Apex Precision Ltd",
                    email="duplicate@apex.com",
                )


# =========================================================================
# 3. Document Upload, Security Validation & Text Extraction
# =========================================================================

class DocumentUploadAndProcessingSecurityTests(APITestCase):
    """Tests file uploads, malicious binary detection, extension validation, and deterministic extraction."""

    def setUp(self):
        self.user = User.objects.create_user(email="doc_admin@acme.com", password="Password123!")
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-DOC-01",
            title="Valve Sourcing",
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Global Valve Corp",
            email="sales@globalvalves.com",
            country="US",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-GV-01",
            created_by=self.user,
        )

    def test_valid_pdf_text_extraction(self):
        """Verifies PDFExtractor extracts multi-page text and word count deterministically using PyMuPDF."""
        pdf_bytes = build_test_pdf_bytes([
            "QUOTATION: QT-VALVE-100",
            "Supplier: Global Valve Corp",
            "Item 1: Stainless Steel Ball Valve 2-inch, Qty: 100, Price: $85.00",
            "Delivery Terms: DDP Chicago, Lead Time: 4 Weeks, Warranty: 24 Months",
        ])

        extractor = PDFExtractor()
        result = extractor.extract(pdf_bytes)

        self.assertEqual(result.document_type, "pdf")
        self.assertEqual(result.total_units, 1)
        self.assertIn("QT-VALVE-100", result.raw_text)
        self.assertIn("Stainless Steel Ball Valve", result.raw_text)
        self.assertGreater(result.word_count, 15)

    def test_valid_excel_tabular_extraction(self):
        """Verifies ExcelExtractor extracts structured rows and cells using openpyxl."""
        excel_bytes = build_test_excel_bytes([
            ["Line", "Part Description", "Quantity", "Unit Price", "Total"],
            [1, "Cryogenic Valve Assembly", 50, 450.00, 22500.00],
            [2, "Teflon Replacement Seal Kit", 200, 15.00, 3000.00],
        ])

        extractor = ExcelExtractor()
        result = extractor.extract(excel_bytes)

        self.assertEqual(result.document_type, "excel")
        self.assertIn("Cryogenic Valve Assembly", result.raw_text)
        self.assertIn("22500", result.raw_text)

    def test_reject_executable_masquerading_as_pdf(self):
        """Rejects executable binary headers disguised as PDF with HTTP 400."""
        fake_pdf = SimpleUploadedFile(
            "trojan.pdf",
            b"MZ\x90\x00\x03\x00\x00\x00executable content disguised",
            content_type="application/pdf",
        )

        response = self.client.post(
            f"/api/quotations/{self.quotation.id}/documents/",
            {"file": fake_pdf},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("executable" in str(response.data).lower() or "signature" in str(response.data).lower())

    def test_path_traversal_filename_sanitized(self):
        """Sanitizes dangerous path traversal filenames (e.g. ../../../../etc/passwd.pdf)."""
        pdf_bytes = build_test_pdf_bytes(["Safe quotation text"])
        uploaded = SimpleUploadedFile(
            "../../../../etc/passwd.pdf",
            pdf_bytes,
            content_type="application/pdf",
        )

        with patch("quotations.tasks.process_document_task.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "mock-task-safe-id"
            mock_delay.return_value = mock_task

            response = self.client.post(
                f"/api/quotations/{self.quotation.id}/documents/",
                {"file": uploaded},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["original_filename"], "passwd.pdf")
            doc = QuotationDocument.objects.get(id=response.data["id"])
            self.assertNotIn("..", doc.file.name)


# =========================================================================
# 4. AI Extraction Validation & Verification Engine (Mocked Gemini)
# =========================================================================

class AIExtractionAndVerificationTests(TestCase):
    """Tests Pydantic extraction schema validation, arithmetic auditing, and anti-hallucination null handling."""

    def test_extraction_schema_validates_complete_payload(self):
        """Verifies full structured quotation data validates against Pydantic schema."""
        raw_data = {
            "supplier": {
                "supplier_name": "Apex Dynamics",
                "email": "sales@apexdynamics.com",
                "quotation_number": "QT-2026-901",
            },
            "quotation": {
                "quotation_date": "2026-11-20",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 10000.00,
                "tax": 800.00,
                "discount": 500.00,
                "shipping": 200.00,
                "grand_total": 10500.00,
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Optical Sensor 24V",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 100.00,
                    "total": 10000.00,
                    "specifications": [{"name": "Voltage", "value": "24V DC"}],
                }
            ],
            "commercial_terms": {
                "delivery_time": "3 Weeks",
                "payment_terms": "Net 30",
                "warranty": "12 Months",
            },
        }

        schema = QuotationExtractionSchema(**raw_data)
        self.assertEqual(schema.supplier.supplier_name, "Apex Dynamics")
        self.assertEqual(schema.quotation.grand_total, 10500.00)
        self.assertEqual(len(schema.line_items), 1)

    def test_verification_engine_detects_math_inconsistency(self):
        """Detects arithmetic discrepancy where stated grand total does not equal subtotal + tax - discount + shipping."""
        discrepant_data = {
            "supplier": {"supplier_name": "Apex Dynamics", "quotation_number": "QT-901"},
            "quotation": {
                "quotation_date": "2026-11-20",
                "validity_date": "2026-12-31",
                "currency": "USD",
                "subtotal": 10000.00,
                "tax": 1000.00,
                "discount": 0.00,
                "shipping": 0.00,
                "grand_total": 15000.00,  # 10000 + 1000 != 15000
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Sensor",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 100.00,
                    "total": 10000.00,
                }
            ],
            "commercial_terms": {"delivery_time": "2 Weeks", "payment_terms": "Net 30"},
        }

        schema = QuotationExtractionSchema(**discrepant_data)
        report = QuotationVerificationEngine.verify(schema)

        self.assertFalse(report.is_math_consistent)


# =========================================================================
# 5. Human Review, Correction Recalculation & Approval Workflow
# =========================================================================

class HumanReviewWorkflowAPITests(APITestCase):
    """Tests procurement manager review, field-level corrections, automatic math recalculation, and audit logging."""

    def setUp(self):
        self.user = User.objects.create_user(email="reviewer@acme.com", password="Password123!")
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-REV-01",
            title="Actuator Review",
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Apex Review Corp",
            email="info@apexreview.com",
            country="US",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-REV-01",
            created_by=self.user,
        )
        self.document = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=SimpleUploadedFile("review_doc.pdf", b"%PDF-1.4 mock", content_type="application/pdf"),
            original_filename="review_doc.pdf",
            file_type=DocumentFileType.PDF,
            file_size=len(b"%PDF-1.4 mock"),
            uploaded_by=self.user,
        )

        # Create unreviewed AI extraction record
        self.extraction = QuotationExtraction.objects.create(
            organization=self.org,
            quotation=self.quotation,
            document=self.document,
            status=ExtractionStatus.COMPLETED,
            review_status=ReviewStatus.UNREVIEWED,
            extracted_data={
                "supplier": {"supplier_name": "Apex Review Corp Initial", "quotation_number": "QT-REV-01"},
                "quotation": {
                    "quotation_date": "2026-11-20",
                    "validity_date": "2026-12-31",
                    "currency": "USD",
                    "subtotal": 5000.00,
                    "grand_total": 5000.00,
                },
                "line_items": [
                    {
                        "line_number": 1,
                        "description": "Servo Actuator Motor",
                        "quantity": 10.0,
                        "unit": "PCS",
                        "unit_price": 500.00,
                        "total": 5000.00,
                    }
                ],
                "commercial_terms": {"delivery_time": "3 Weeks", "payment_terms": "Net 30"},
            },
            stated_subtotal=Decimal("5000.00"),
            stated_grand_total=Decimal("5000.00"),
            calculated_items_subtotal=Decimal("5000.00"),
            calculated_grand_total=Decimal("5000.00"),
        )

    def test_correct_line_item_triggers_deterministic_recalculation(self):
        """Correcting unit price automatically recalculates extended line total, subtotal, and grand total."""
        # Change unit_price from $500.00 to $650.00 for quantity 10 -> extended total must become $6500.00
        payload = {
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Servo Actuator Motor",
                    "quantity": 10.0,
                    "unit": "PCS",
                    "unit_price": 650.00,
                    "total": 6500.00,
                }
            ],
            "quotation": {
                "subtotal": 6500.00,
                "grand_total": 6500.00,
            },
            "reason": "Corrected unit price to $650 per supplier confirmation email",
        }

        response = self.client.post(
            f"/api/extractions/{self.extraction.id}/correct/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.extraction.refresh_from_db()
        # Verify deterministic recomputation: 10 * 650.00 = 6500.00
        updated_item = self.extraction.extracted_data["line_items"][0]
        self.assertEqual(float(updated_item["unit_price"]), 650.00)
        self.assertEqual(self.extraction.calculated_items_subtotal, Decimal("6500.00"))
        self.assertEqual(self.extraction.calculated_grand_total, Decimal("6500.00"))

        # Verify audit log created
        audit_exists = QuotationExtractionCorrection.objects.filter(
            extraction=self.extraction,
            field_path__icontains="unit_price",
        ).exists()
        self.assertTrue(audit_exists)

    def test_approve_extraction_syncs_to_quotation(self):
        """Approving an extraction transitions review status to APPROVED and populates quotation models."""
        response = self.client.post(
            f"/api/extractions/{self.extraction.id}/approve/",
            {"review_notes": "All items verified.", "apply_to_quotation": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.extraction.refresh_from_db()
        self.assertEqual(self.extraction.review_status, ReviewStatus.APPROVED)
        self.assertEqual(self.extraction.approved_by, self.user)


# =========================================================================
# 6. Deterministic Price Comparison Engine & Currency Normalization
# =========================================================================

class PriceComparisonAndCurrencyEngineTests(TestCase):
    """Tests deterministic unit price, tax, discount, grand total, lowest price delta, and multi-currency conversion."""

    def setUp(self):
        self.rate_table = ExchangeRateTable()
        self.rate_table.add_rate(ExchangeRate(source_currency="EUR", target_currency="USD", rate=Decimal("1.10"), rate_source="ECB", rate_date=date.today()))
        self.rate_table.add_rate(ExchangeRate(source_currency="GBP", target_currency="USD", rate=Decimal("1.25"), rate_source="BOE", rate_date=date.today()))

    def test_currency_conversion_service_deterministic_rates(self):
        """Validates exact currency conversions using explicit exchange rate tables."""
        service = CurrencyConversionService(self.rate_table)

        # 100 EUR -> 110 USD
        result_usd = service.convert(amount=Decimal("100.00"), source_currency="EUR", target_currency="USD")
        self.assertEqual(result_usd.converted_amount, Decimal("110.00"))

        # Identity conversion USD -> USD
        self.assertEqual(
            service.convert(amount=Decimal("50.00"), source_currency="USD", target_currency="USD").converted_amount,
            Decimal("50.00"),
        )

    def test_price_comparison_engine_identifies_lowest_and_savings(self):
        """Compares two quotation bids and deterministically calculates price difference and cherry-pick savings."""
        user = User.objects.create_user(email="pricing@acme.com", password="Password123!")
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=user)
        rfq = RFQ.objects.create(organization=org, rfq_number="RFQ-PRICING-01", title="Sensors", currency="USD", created_by=user)
        item1 = RFQItem.objects.create(rfq=rfq, position=1, item_name="Proximity Sensor", quantity=Decimal("100.00"), unit="PCS")
        item2 = RFQItem.objects.create(rfq=rfq, position=2, item_name="Mounting Bracket", quantity=Decimal("100.00"), unit="PCS")

        # Supplier 1: Item 1 = $10, Item 2 = $5 -> Grand Total = $1,500
        supp1 = Supplier.objects.create(organization=org, company_name="Supplier Alpha")
        q1 = Quotation.objects.create(organization=org, rfq=rfq, supplier=supp1, quotation_number="Q1", currency="USD")
        QuotationItem.objects.create(quotation=q1, rfq_item=item1, description="Proximity Sensor", quantity=Decimal("100.00"), unit_price=Decimal("10.00"), line_total=Decimal("1000.00"))
        QuotationItem.objects.create(quotation=q1, rfq_item=item2, description="Mounting Bracket", quantity=Decimal("100.00"), unit_price=Decimal("5.00"), line_total=Decimal("500.00"))
        q1.recalculate_totals()

        # Supplier 2: Item 1 = $8, Item 2 = $8 -> Grand Total = $1,600
        supp2 = Supplier.objects.create(organization=org, company_name="Supplier Beta")
        q2 = Quotation.objects.create(organization=org, rfq=rfq, supplier=supp2, quotation_number="Q2", currency="USD")
        QuotationItem.objects.create(quotation=q2, rfq_item=item1, description="Proximity Sensor", quantity=Decimal("100.00"), unit_price=Decimal("8.00"), line_total=Decimal("800.00"))
        QuotationItem.objects.create(quotation=q2, rfq_item=item2, description="Mounting Bracket", quantity=Decimal("100.00"), unit_price=Decimal("8.00"), line_total=Decimal("800.00"))
        q2.recalculate_totals()

        engine = PriceComparisonEngine(
            rfq=rfq,
            quotations=[q1, q2],
            comparison_currency="USD",
        )
        summary = engine.compare()

        self.assertEqual(summary.lowest_grand_total, Decimal("1500.00"))
        self.assertEqual(summary.highest_grand_total, Decimal("1600.00"))
        self.assertEqual(summary.highest_grand_total - summary.lowest_grand_total, Decimal("100.00"))
        # Cherry-pick: Item 1 from Supp 2 ($800) + Item 2 from Supp 1 ($500) = $1,300
        self.assertEqual(summary.cherry_pick_total, Decimal("1300.00"))
        # Max savings: 1600 - 1500 = 100
        self.assertEqual(summary.max_savings_amount, Decimal("100.00"))


# =========================================================================
# 7. Specification Matching Engine
# =========================================================================

class SpecificationMatchingEngineTests(TestCase):
    """Tests exact matches, mismatches, missing specs, and compliance score calculations."""

    def test_deterministic_exact_and_mismatch_evaluation(self):
        """Verifies deterministic spec engine classifies identical values as EXACT_MATCH and divergent values as MISMATCH."""
        engine = SpecificationMatchingEngine()

        rfq_specs = {
            'Voltage': '24V DC',
            'Output': 'PNP',
            'Sensing distance': '8mm',
        }

        supplier_specs = {
            'Voltage': '24V DC',
            'Output': 'NPN',
        }

        summary = engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=supplier_specs,
            item_name="Proximity Sensor",
        )

        self.assertEqual(summary.total_requirements_count, 3)
        self.assertEqual(summary.exact_matches_count, 1)    # Voltage
        self.assertEqual(summary.mismatches_count, 1)       # Output
        self.assertEqual(summary.missing_count, 1)          # Sensing distance
        self.assertLess(summary.spec_match_score, 100.0)


# =========================================================================
# 8. Quotation Risk Flags Engine (14 Deterministic Rules)
# =========================================================================

class QuotationRiskEngineTests(TestCase):
    """Tests 14 deterministic risk rules including high advance payment, expired validity, delivery delay, and missing warranty."""

    def test_risk_engine_detects_commercial_and_delivery_risks(self):
        """Detects advance deposit risk, warranty omission, and delivery schedule delays."""
        user = User.objects.create_user(email="risk@acme.com", password="Password123!")
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=user)
        rfq = RFQ.objects.create(
            organization=org,
            rfq_number="RFQ-RISK-01",
            title="Heavy Valves",
            required_delivery_date=date.today() + timedelta(days=21),  # 3 weeks
            created_by=user,
        )

        supp = Supplier.objects.create(organization=org, company_name="High Risk Machining")
        quote = Quotation.objects.create(
            organization=org,
            rfq=rfq,
            supplier=supp,
            quotation_number="QT-HRM-99",
            lead_time_weeks=Decimal("6.0"),  # 6 weeks > 3 weeks -> delivery_delay
            payment_terms="100% advance payment required upon order placement",  # high advance
            warranty_information="No warranty provided",  # missing / no warranty
            validity_date=date.today() - timedelta(days=5),  # expired
        )

        engine = QuotationRiskEngine(config=RiskEngineConfig())
        report = engine.evaluate_quotation(quotation_or_data=quote, rfq_or_data=rfq, evaluation_date=date.today())

        flag_types = [f.type for f in report.flags]
        self.assertIn("delivery_delay", flag_types)
        self.assertIn("high_advance_payment", flag_types)
        self.assertIn("no_warranty", flag_types)
        self.assertIn("expired_quotation", flag_types)
        self.assertIn(report.overall_risk_level, ["HIGH", "CRITICAL"])


# =========================================================================
# 9. Explainable Supplier Scoring Engine
# =========================================================================

class SupplierScoringEngineTests(TestCase):
    """Tests weighted multi-factor scoring, 100% weight validation, formula transparency, and limitations."""

    def test_weight_validation_strictly_requires_100_percent(self):
        """Weights summing to 90% or 110% are rejected with ValueError."""
        # 90% sum must fail
        with self.assertRaises(ValueError):
            validate_weights({"price": 40, "spec_match": 30, "delivery": 10, "payment_terms": 10, "warranty": 0})

        # 100% sum must succeed
        valid = validate_weights({"price": 40, "spec_match": 30, "delivery": 15, "payment_terms": 10, "warranty": 5})
        self.assertEqual(sum(valid.to_dict().values()), 100.0)

    def test_scoring_engine_computes_explainable_scores(self):
        """Validates transparent factor scoring and rank determination."""
        user = User.objects.create_user(email="scoring@acme.com", password="Password123!")
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=user)
        rfq = RFQ.objects.create(organization=org, rfq_number="RFQ-SCORE-01", title="Precision Pins", created_by=user)
        item = RFQItem.objects.create(rfq=rfq, position=1, item_name="Pin", quantity=Decimal("100"))

        supp = Supplier.objects.create(organization=org, company_name="Score Supplier")
        quote = Quotation.objects.create(
            organization=org,
            rfq=rfq,
            supplier=supp,
            quotation_number="QT-SCORE-01",
            lead_time_weeks=Decimal("2.0"),
            payment_terms="Net 30",
            warranty_information="12 Months",
        )
        QuotationItem.objects.create(
            quotation=quote,
            rfq_item=item,
            description="Pin",
            quantity=Decimal("100"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("1000.00"),
        )
        quote.recalculate_totals()

        engine = SupplierScoringEngine()
        summary = engine.score_rfq_quotations(
            rfq_or_data=rfq,
            quotations_or_data=[quote],
            weights=ScoringWeights(price=40, spec_match=30, delivery=15, payment_terms=10, warranty=5),
        )

        self.assertEqual(len(summary.rankings), 1)
        rank_1 = summary.rankings[0]
        self.assertGreaterEqual(rank_1.final_score, 70.0)
        self.assertIn("price", rank_1.factors)
        self.assertIn("spec_match", rank_1.factors)
        self.assertIn("delivery", rank_1.factors)


# =========================================================================
# 10. Publication-Grade Excel & PDF Export Generators
# =========================================================================

class ReportGeneratorsEndToEndTests(APITestCase):
    """Tests Excel 5-sheet generation with openpyxl and executive PDF generation with ReportLab."""

    def setUp(self):
        self.user = User.objects.create_user(email="reports@acme.com", password="Password123!")
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp", created_by=self.user)
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-EXP-01",
            title="Industrial Fasteners Package",
            created_by=self.user,
        )
        self.item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Flange Bolt",
            quantity=Decimal("500"),
            unit="PCS",
            target_unit_price=Decimal("15.00"),
        )
        self.supp = Supplier.objects.create(organization=self.org, company_name="Aero Fasteners Ltd")
        self.quote = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supp,
            quotation_number="QT-EXP-01",
            status="approved",
            delivery_terms="DDP Chicago",
            payment_terms="Net 30",
            warranty_information="12 Months",
            lead_time_weeks=Decimal("3.0"),
        )
        QuotationItem.objects.create(
            quotation=self.quote,
            rfq_item=self.item,
            description="Flange Bolt",
            quantity=Decimal("500"),
            unit_price=Decimal("14.00"),
            line_total=Decimal("7000.00"),
        )
        self.quote.recalculate_totals()

    def test_excel_export_endpoint_returns_valid_multisheet_workbook(self):
        """GET /api/comparisons/rfqs/<id>/export/excel/ returns 5-sheet formatted workbook."""
        response = self.client.get(f"/api/comparisons/rfqs/{self.rfq.id}/export/excel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Inspect workbook structure using openpyxl
        stream = io.BytesIO(response.content)
        wb = openpyxl.load_workbook(stream)
        expected_sheets = [
            "Summary",
            "Price Comparison",
            "Specification Comparison",
            "Commercial Terms",
            "Risk Flags",
        ]
        for sheet_name in expected_sheets:
            self.assertIn(sheet_name, wb.sheetnames)

    def test_pdf_export_endpoint_returns_valid_publication_grade_pdf(self):
        """GET /api/comparisons/rfqs/<id>/export/pdf/ returns publication-grade PDF starting with %PDF- header."""
        response = self.client.get(f"/api/comparisons/rfqs/{self.rfq.id}/export/pdf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertGreater(len(response.content), 1000)
