"""
Test Suite for QuoteFlow AI Excel Report Generation Service and Export APIs.
Verifies publication-grade 5-sheet Excel workbook export:
- Sheet 1: Summary
- Sheet 2: Price Comparison
- Sheet 3: Specification Comparison
- Sheet 4: Commercial Terms
- Sheet 5: Risk Flags
Also tests REST API endpoints and tenant isolation.
"""
from datetime import date, timedelta
from decimal import Decimal
import io
import uuid
import openpyxl

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from extractions.models import QuotationExtraction, ReviewStatus
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from quotations.models import Quotation, QuotationItem, QuotationStatus, QuotationDocument
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier
import fitz  # PyMuPDF
from reports.excel_generator import RFQComparisonExcelGenerator
from reports.services import (
    generate_rfq_comparison_excel_workbook,
    generate_rfq_comparison_excel_bytes,
    generate_rfq_comparison_pdf_bytes,
)

User = get_user_model()


class ExcelReportGenerationTests(APITestCase):
    """
    Unit and integration tests for Excel workbook generation and export APIs.
    """

    def setUp(self):
        # 1. Organization A (Tenant Alpha)
        self.org_a = Organization.objects.create(
            name="Alpha Aerospace Dynamics",
            slug=f"alpha-aero-{uuid.uuid4().hex[:8]}",
        )
        self.user_a = User.objects.create_user(
            email=f"procurement-a-{uuid.uuid4().hex[:6]}@alpha.com",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="Procurement",
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationRole.ADMIN,
            is_active=True,
        )

        # 2. Organization B (Tenant Beta - Attacker)
        self.org_b = Organization.objects.create(
            name="Beta Motors",
            slug=f"beta-motors-{uuid.uuid4().hex[:8]}",
        )
        self.user_b = User.objects.create_user(
            email=f"procurement-b-{uuid.uuid4().hex[:6]}@beta.com",
            password="SecurePassword123!",
            first_name="Bob",
            last_name="Beta",
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationRole.ADMIN,
            is_active=True,
        )

        # 3. Suppliers
        self.supplier_1 = Supplier.objects.create(
            organization=self.org_a,
            company_name="Apex Precision Engineering",
            email="sales@apex.com",
            contact_person="Alice Apex",
        )
        self.supplier_2 = Supplier.objects.create(
            organization=self.org_a,
            company_name="Vanguard Dynamics",
            email="quotes@vanguard.com",
            contact_person="Victor Vanguard",
        )

        # 4. Target RFQ in Org A
        self.today = date.today()
        self.rfq = RFQ.objects.create(
            organization=self.org_a,
            rfq_number=f"RFQ-2026-{uuid.uuid4().hex[:4].upper()}",
            title="CNC High-Tolerance Proximity Sensor Housing",
            currency="USD",
            required_delivery_date=self.today + timedelta(days=28),
            status=RFQStatus.OPEN,
            created_by=self.user_a,
        )

        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Sensor Housing M12",
            description="M12 threaded sensor housing, 24V DC, PNP, 8mm sensing",
            quantity=Decimal('10'),
            unit="PCS",
            target_unit_price=Decimal('450.00'),
            custom_specifications={
                'Voltage': '24V DC',
                'Output': 'PNP',
                'Sensing Distance': '8mm',
                'Connection': 'M12',
            },
        )

        # 5. Approved Quotation 1 (Apex: $400/ea = $4,000, 100% compliant, Net 30, 24 mo warranty)
        self.quote_1 = Quotation.objects.create(
            organization=self.org_a,
            rfq=self.rfq,
            supplier=self.supplier_1,
            quotation_number="APEX-QUOTE-101",
            quotation_date=self.today - timedelta(days=2),
            validity_date=self.today + timedelta(days=60),
            currency="USD",
            subtotal=Decimal('4000.00'),
            tax_amount=Decimal('200.00'),
            total_amount=Decimal('4200.00'),
            payment_terms="Net 30 days",
            warranty_information="24 months manufacturer warranty",
            delivery_terms="DAP Austin",
            lead_time_weeks=Decimal('3.0'),
            status=QuotationStatus.RECEIVED,
        )
        QuotationItem.objects.create(
            quotation=self.quote_1,
            position=1,
            rfq_item=self.rfq_item,
            description="Sensor Housing M12 Threaded",
            quantity=Decimal('10'),
            unit="PCS",
            unit_price=Decimal('400.00'),
            line_total=Decimal('4000.00'),
            specifications={
                'Voltage': '24V DC',
                'Output': 'PNP',
                'Sensing Distance': '8mm',
                'Connection': 'M12',
            },
        )
        doc_1 = QuotationDocument.objects.create(
            organization=self.org_a,
            quotation=self.quote_1,
            original_filename="Apex_Quote_101.pdf",
            file_size=102400,
            file_type="pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            checksum_sha256=uuid.uuid4().hex,
        )
        QuotationExtraction.objects.create(
            organization=self.org_a,
            document=doc_1,
            extracted_data={'confidence': 0.98},
            review_status=ReviewStatus.APPROVED,
            reviewed_by=self.user_a,
            reviewed_at=timezone.now(),
        )

        # 6. Approved Quotation 2 (Vanguard: $480/ea = $4,800, NPN mismatch, 50% advance deposit, 6 weeks lead time)
        self.quote_2 = Quotation.objects.create(
            organization=self.org_a,
            rfq=self.rfq,
            supplier=self.supplier_2,
            quotation_number="VANGUARD-QUOTE-202",
            quotation_date=self.today - timedelta(days=1),
            validity_date=self.today + timedelta(days=45),
            currency="USD",
            subtotal=Decimal('4800.00'),
            tax_amount=Decimal('240.00'),
            total_amount=Decimal('5040.00'),
            payment_terms="50% Advance Deposit, balance on delivery",
            warranty_information="12 months standard warranty",
            delivery_terms="EXW Dallas",
            lead_time_weeks=Decimal('6.0'),
            status=QuotationStatus.RECEIVED,
        )
        QuotationItem.objects.create(
            quotation=self.quote_2,
            position=1,
            rfq_item=self.rfq_item,
            description="Sensor Housing M12 (NPN Output)",
            quantity=Decimal('10'),
            unit="PCS",
            unit_price=Decimal('480.00'),
            line_total=Decimal('4800.00'),
            specifications={
                'Voltage': '24V DC',
                'Output': 'NPN',
                'Sensing Distance': '8mm',
                'Connection': 'M12',
            },
        )
        doc_2 = QuotationDocument.objects.create(
            organization=self.org_a,
            quotation=self.quote_2,
            original_filename="Vanguard_Quote_202.pdf",
            file_size=204800,
            file_type="pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            checksum_sha256=uuid.uuid4().hex,
        )
        QuotationExtraction.objects.create(
            organization=self.org_a,
            document=doc_2,
            extracted_data={'confidence': 0.95},
            review_status=ReviewStatus.APPROVED,
            reviewed_by=self.user_a,
            reviewed_at=timezone.now(),
        )

    # -------------------------------------------------------------------------
    # Unit Tests for RFQComparisonExcelGenerator Service
    # -------------------------------------------------------------------------
    def test_workbook_has_all_five_required_sheets(self):
        """Verifies the workbook contains all 5 mandatory sheets in exact order."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        sheet_names = wb.sheetnames
        expected_sheets = [
            "Summary",
            "Price Comparison",
            "Specification Comparison",
            "Commercial Terms",
            "Risk Flags",
        ]
        self.assertEqual(sheet_names, expected_sheets)

    def test_summary_sheet_content_and_guardrail(self):
        """Verifies Summary sheet renders RFQ metadata, KPIs, suppliers, and decision support disclaimer."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        ws = wb["Summary"]

        # Title and RFQ Number
        self.assertIn("QuoteFlow AI", str(ws['A1'].value))
        self.assertIn(self.rfq.rfq_number, str(ws['A2'].value))

        # Check that suppliers are listed in the sheet
        found_apex = False
        found_vanguard = False
        found_guardrail = False

        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(c) for c in row if c is not None])
            if "Apex Precision" in row_text:
                found_apex = True
            if "Vanguard Dynamics" in row_text:
                found_vanguard = True
            if "DECISION-SUPPORT GUARDRAIL" in row_text.upper():
                found_guardrail = True

        self.assertTrue(found_apex, "Apex Precision should be present in Summary sheet")
        self.assertTrue(found_vanguard, "Vanguard Dynamics should be present in Summary sheet")
        self.assertTrue(found_guardrail, "Guardrail disclaimer must be present in Summary sheet")

    def test_price_comparison_sheet_content(self):
        """Verifies Price Comparison sheet contains financial summary and itemized BOM schedule."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        ws = wb["Price Comparison"]

        found_bom_item = False
        found_grand_total = False

        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(c) for c in row if c is not None])
            if "Sensor Housing M12" in row_text:
                found_bom_item = True
            if "4200" in row_text or "5040" in row_text or "4000" in row_text:
                found_grand_total = True

        self.assertTrue(found_bom_item, "BOM Item must be listed on Price Comparison sheet")
        self.assertTrue(found_grand_total, "Quoted grand totals must be present on Price Comparison sheet")

    def test_specification_comparison_sheet_content(self):
        """Verifies Specification Comparison sheet lists parameter matches, statuses, and explanations."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        ws = wb["Specification Comparison"]

        found_match = False
        found_mismatch = False

        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(c) for c in row if c is not None])
            if "EXACT_MATCH" in row_text or "COMPLIANT" in row_text:
                found_match = True
            if "MISMATCH" in row_text or "NPN" in row_text:
                found_mismatch = True

        self.assertTrue(found_match, "Specification sheet must identify exact matches or compliant items")
        self.assertTrue(found_mismatch, "Specification sheet must identify NPN mismatch for Vanguard")

    def test_commercial_terms_sheet_content(self):
        """Verifies Commercial Terms sheet lists lead times, Incoterms, payment terms, and warranty."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        ws = wb["Commercial Terms"]

        found_payment_terms = False
        found_warranty = False

        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(c) for c in row if c is not None])
            if "Net 30" in row_text or "Advance Deposit" in row_text:
                found_payment_terms = True
            if "24 months" in row_text or "12 months" in row_text:
                found_warranty = True

        self.assertTrue(found_payment_terms, "Commercial terms sheet must list payment terms")
        self.assertTrue(found_warranty, "Commercial terms sheet must list warranty terms")

    def test_risk_flags_sheet_content(self):
        """Verifies Risk Flags sheet contains deterministic risk flags with severity and recommendations."""
        wb = generate_rfq_comparison_excel_workbook(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        ws = wb["Risk Flags"]

        found_risk = False
        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(c) for c in row if c is not None])
            if "HIGH" in row_text or "MEDIUM" in row_text or "deposit" in row_text.lower() or "mismatch" in row_text.lower():
                found_risk = True
                break

        self.assertTrue(found_risk, "Risk Flags sheet must document flagged commercial/technical risks")

    # -------------------------------------------------------------------------
    # REST API Endpoint Tests
    # -------------------------------------------------------------------------
    def test_export_excel_api_reports_endpoint(self):
        """Tests GET /api/reports/rfqs/{rfq_id}/excel/ downloads a valid 5-sheet workbook."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse('reports:export-rfq-comparison-excel', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_a.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment; filename=', response['Content-Disposition'])
        self.assertIn('.xlsx', response['Content-Disposition'])

        # Parse downloaded binary payload with openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertEqual(len(wb.sheetnames), 5)
        self.assertIn("Summary", wb.sheetnames)
        self.assertIn("Price Comparison", wb.sheetnames)

    def test_export_excel_api_comparisons_endpoint(self):
        """Tests GET /api/comparisons/rfqs/{rfq_id}/export/excel/ alias endpoint."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse('comparisons:rfq-export-excel', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_a.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertEqual(len(wb.sheetnames), 5)

    def test_tenant_isolation_prevents_cross_org_export(self):
        """Verifies User B in Organization B cannot export Organization A's RFQ (returns 404)."""
        self.client.force_authenticate(user=self.user_b)
        url = reverse('reports:export-rfq-comparison-excel', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_b.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        """Verifies unauthenticated calls to export are rejected with 401."""
        url = reverse('reports:export-rfq-comparison-excel', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # PDF Comparison Report Generation & Export Tests
    # -------------------------------------------------------------------------
    def test_pdf_report_generator_creates_valid_pdf_stream(self):
        """Verifies PDF report generator creates a valid PDF document with all required procurement sections."""
        pdf_buf = generate_rfq_comparison_pdf_bytes(rfq=self.rfq, organization=self.org_a, user=self.user_a)
        pdf_bytes = pdf_buf.getvalue()

        # 1. Verify standard PDF magic header
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'), "PDF document must start with standard %PDF- header")
        self.assertGreater(len(pdf_bytes), 2000, "PDF payload must be substantial")

        # 2. Inspect document structure using PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.assertGreaterEqual(doc.page_count, 1, "PDF document must contain at least 1 page")

        # Extract text across all pages
        full_text = " ".join([page.get_text() for page in doc])

        # Verify key procurement sections and data points
        self.assertIn("QuoteFlow AI", full_text)
        self.assertIn(self.rfq.rfq_number, full_text)
        self.assertIn("Apex Precision", full_text)
        self.assertIn("Vanguard Dynamics", full_text)
        self.assertIn("1. RFQ Scope & Procurement Baseline", full_text)
        self.assertIn("2. Overall Supplier Evaluation", full_text)
        self.assertIn("3. Detailed Price Comparison", full_text)
        self.assertIn("4. Technical Specification Matching", full_text)
        self.assertIn("5. Commercial Terms", full_text)
        self.assertIn("6. Deterministic Quotation Risk Flags", full_text)
        self.assertIn("7. Explainable Supplier Scoring Engine", full_text)
        self.assertIn("8. Strategic Award Recommendation", full_text)
        self.assertIn("DECISION-SUPPORT GUARDRAIL", full_text)
        self.assertIn("CONFIDENTIAL", full_text)
        self.assertIn("Page 1 of", full_text)

    def test_export_pdf_api_reports_endpoint(self):
        """Tests GET /api/reports/rfqs/{rfq_id}/pdf/ downloads a valid PDF report."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse('reports:export-rfq-comparison-pdf', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_a.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename=', response['Content-Disposition'])
        self.assertIn('.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

        # Parse with PyMuPDF
        doc = fitz.open(stream=response.content, filetype="pdf")
        self.assertGreaterEqual(doc.page_count, 1)

    def test_export_pdf_api_comparisons_endpoint(self):
        """Tests GET /api/comparisons/rfqs/{rfq_id}/export/pdf/ alias endpoint."""
        self.client.force_authenticate(user=self.user_a)
        url = reverse('comparisons:rfq-export-pdf', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_a.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_tenant_isolation_prevents_cross_org_pdf_export(self):
        """Verifies User B in Org B cannot export Org A's RFQ PDF (returns 404)."""
        self.client.force_authenticate(user=self.user_b)
        url = reverse('reports:export-rfq-comparison-pdf', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url, HTTP_X_ORGANIZATION_ID=str(self.org_b.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected_for_pdf(self):
        """Verifies unauthenticated calls to PDF export are rejected with 401."""
        url = reverse('reports:export-rfq-comparison-pdf', kwargs={'rfq_id': self.rfq.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

