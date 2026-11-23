"""
Automated test suite for AI Quotation Extraction in QuoteFlow AI.
Tests Pydantic schema validation, prompt generation, arithmetic auditing,
anti-hallucination null handling, synchronization to Quotation line items,
and API tenant isolation.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from extractions.models import ExtractionStatus, QuotationExtraction
from extractions.prompts import build_quotation_extraction_prompt
from extractions.schemas import (
    CommercialTermsSchema,
    EvidenceCollectionSchema,
    FieldEvidence,
    LineItemSchema,
    QuotationExtractionSchema,
    QuotationInfoSchema,
    SpecificationItem,
    SupplierInfoSchema,
)
from extractions.services import QuotationExtractionService
from extractions.verification import QuotationVerificationEngine
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from quotations.models import (
    DocumentFileType,
    DocumentProcessingStatus,
    Quotation,
    QuotationDocument,
    QuotationItem,
)
from rfqs.models import RFQ, RFQStatus
from suppliers.models import Supplier
from users.models import User


class QuotationExtractionSchemaTests(APITestCase):
    """Unit tests for Pydantic v2 extraction schemas."""

    def test_schema_validates_complete_payload(self):
        """Verifies full quotation data with line items and evidence validates successfully."""
        data = {
            "supplier": {
                "supplier_name": "Apex Dynamics Ltd",
                "contact_person": "Sarah Jenkins",
                "email": "sarah@apexdynamics.com",
                "phone": "+1-555-0199",
                "address": "1200 Industrial Pkwy, Chicago, IL",
                "quotation_number": "QT-2026-9001",
            },
            "quotation": {
                "quotation_date": "2026-11-20",
                "validity_date": "2026-12-20",
                "currency": "USD",
                "subtotal": 12500.00,
                "tax": 1000.00,
                "discount": 500.00,
                "shipping": 250.00,
                "grand_total": 13250.00,
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "High-Pressure Hydraulic Pump",
                    "manufacturer": "Apex",
                    "model": "HPP-500",
                    "quantity": 2.0,
                    "unit": "PCS",
                    "unit_price": 5000.00,
                    "discount": 200.00,
                    "tax": 400.00,
                    "total": 10200.00,
                    "specifications": [
                        {"name": "Pressure", "value": "5000 PSI"},
                        {"name": "Fluid", "value": "Hydraulic Oil ISO 46"},
                    ],
                    "source_text": "Item 1: HPP-500 Pump 2 PCS @ $5,000",
                    "page_number": 1,
                    "confidence_level": 0.95,
                }
            ],
            "commercial_terms": {
                "delivery_time": "3 weeks ARO",
                "delivery_terms": "FOB Chicago",
                "payment_terms": "Net 30",
                "warranty": "24 Months",
                "notes": "Standard industrial packaging included.",
            },
            "evidence": {
                "supplier_name": {
                    "extracted_value": "Apex Dynamics Ltd",
                    "source_text": "Apex Dynamics Ltd - Official Proposal",
                    "page_number": 1,
                    "confidence_level": 0.98,
                },
                "grand_total": {
                    "extracted_value": "13250.00",
                    "source_text": "TOTAL PAYABLE: $13,250.00 USD",
                    "page_number": 2,
                    "confidence_level": 0.99,
                },
            },
            "overall_confidence": 0.96,
            "summary": "Commercial proposal for 2 hydraulic pumps with 3-week delivery.",
        }

        schema_obj = QuotationExtractionSchema.model_validate(data)
        self.assertEqual(schema_obj.supplier.supplier_name, "Apex Dynamics Ltd")
        self.assertEqual(len(schema_obj.line_items), 1)
        self.assertEqual(schema_obj.line_items[0].specifications[0].name, "Pressure")
        self.assertEqual(schema_obj.evidence.grand_total.page_number, 2)

    def test_schema_null_handling_for_missing_fields(self):
        """Verifies that missing fields default safely to None without hallucination."""
        minimal_data = {
            "supplier": {},
            "quotation": {},
            "line_items": [
                {
                    "description": "Generic Steel Plate",
                }
            ],
            "commercial_terms": {},
            "evidence": {},
        }
        schema_obj = QuotationExtractionSchema.model_validate(minimal_data)
        self.assertIsNone(schema_obj.supplier.supplier_name)
        self.assertIsNone(schema_obj.quotation.grand_total)
        self.assertIsNone(schema_obj.line_items[0].unit_price)
        self.assertIsNone(schema_obj.commercial_terms.payment_terms)


class VerificationEngineTests(APITestCase):
    """Tests independent arithmetic and logical verification."""

    def test_verification_detects_math_consistency(self):
        """Verifies arithmetic consistency passes when numbers add up."""
        data = QuotationExtractionSchema(
            supplier=SupplierInfoSchema(supplier_name="Valid Supplier", quotation_number="QT-100"),
            quotation=QuotationInfoSchema(
                quotation_date="2026-11-20",
                validity_date="2026-12-20",
                currency="USD",
                subtotal=200.00,
                tax=20.00,
                shipping=10.00,
                discount=0.00,
                grand_total=230.00,
            ),
            line_items=[
                LineItemSchema(
                    line_number=1,
                    description="Widget A",
                    quantity=10,
                    unit_price=20.00,
                    total=200.00,
                )
            ],
            commercial_terms=CommercialTermsSchema(payment_terms="Net 30"),
        )
        audit = QuotationVerificationEngine.verify(data)
        self.assertTrue(audit.is_math_consistent)
        self.assertEqual(audit.calculated_items_subtotal, Decimal('200.00'))
        self.assertEqual(audit.calculated_grand_total, Decimal('230.00'))
        self.assertEqual(audit.total_variance, Decimal('0.00'))

    def test_verification_detects_math_discrepancy(self):
        """Verifies discrepancy is flagged when stated grand total does not match line item sum."""
        data = QuotationExtractionSchema(
            supplier=SupplierInfoSchema(supplier_name="Suspicious Vendor", quotation_number="QT-200"),
            quotation=QuotationInfoSchema(
                quotation_date="2026-11-20",
                validity_date="2026-12-20",
                currency="USD",
                subtotal=200.00,
                tax=0.00,
                shipping=0.00,
                discount=0.00,
                grand_total=350.00,  # $150 discrepancy!
            ),
            line_items=[
                LineItemSchema(
                    line_number=1,
                    description="Widget B",
                    quantity=10,
                    unit_price=20.00,
                    total=200.00,
                )
            ],
            commercial_terms=CommercialTermsSchema(payment_terms="Net 30"),
        )
        audit = QuotationVerificationEngine.verify(data)
        self.assertFalse(audit.is_math_consistent)
        self.assertEqual(audit.total_variance, Decimal('150.00'))
        self.assertTrue(any("Grand Total discrepancy" in w for w in audit.validation_warnings))

    def test_verification_detects_date_inversion(self):
        """Verifies warning when validity date is earlier than quotation date."""
        data = QuotationExtractionSchema(
            supplier=SupplierInfoSchema(supplier_name="Time Travel Supplies"),
            quotation=QuotationInfoSchema(
                quotation_date="2026-11-20",
                validity_date="2026-11-10",  # Expired before issued!
            ),
            line_items=[],
            commercial_terms=CommercialTermsSchema(),
        )
        audit = QuotationVerificationEngine.verify(data)
        self.assertFalse(audit.is_math_consistent)
        self.assertTrue(any("Date anomaly" in w for w in audit.validation_warnings))


class QuotationExtractionServiceTests(APITestCase):
    """Integration tests for QuotationExtractionService with mocked Gemini AI calls."""

    def setUp(self):
        self.org = Organization.objects.create(name="Precision Aero Corp", slug="precision-aero-corp")
        self.user = User.objects.create_user(
            email="buyer@precisionaero.com",
            password="SecurePassword123!",
            first_name="Procurement",
            last_name="Buyer",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-AI-01",
            title="Titanium Fasteners Procurement",
            status=RFQStatus.OPEN,
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Vanguard Fasteners Inc",
            contact_person="Dave Miller",
            email="dave@vanguard.com",
            country="United States",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-PENDING-EXTRACT",
            currency="USD",
            created_by=self.user,
        )

        dummy_pdf = b"%PDF-1.4 dummy quotation content"
        uploaded = SimpleUploadedFile("vanguard_quote.pdf", dummy_pdf, content_type="application/pdf")
        self.document = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="vanguard_quote.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(dummy_pdf),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        # Pre-seed text extraction result
        from quotations.models import DocumentExtractionResult
        DocumentExtractionResult.objects.create(
            organization=self.org,
            document=self.document,
            document_type="pdf",
            raw_text="Vanguard Fasteners Inc\nQuote: QT-VG-9921\nItem 1: Titanium Bolt M10, Qty: 50, Price: $25.00, Total: $1250.00\nSubtotal: $1250.00\nTotal: $1250.00",
            pages_or_sheets_count=1,
            character_count=180,
            word_count=25,
            structured_content={"pages": [{"page_number": 1, "text": "Vanguard Fasteners Quote: QT-VG-9921..."}]},
        )

    @patch('ai.service.GeminiService.generate_structured')
    def test_extract_from_document_success(self, mock_generate):
        """Tests end-to-end AI extraction pipeline creates QuotationExtraction record."""
        mock_parsed = QuotationExtractionSchema(
            supplier=SupplierInfoSchema(
                supplier_name="Vanguard Fasteners Inc",
                quotation_number="QT-VG-9921",
                contact_person="Dave Miller",
                email="dave@vanguard.com",
            ),
            quotation=QuotationInfoSchema(
                quotation_date="2026-11-20",
                validity_date="2026-12-20",
                currency="USD",
                subtotal=1250.00,
                tax=0.00,
                shipping=0.00,
                discount=0.00,
                grand_total=1250.00,
            ),
            line_items=[
                LineItemSchema(
                    line_number=1,
                    description="Titanium Bolt M10x50",
                    manufacturer="Vanguard",
                    model="TB-M10-50",
                    quantity=50.0,
                    unit="PCS",
                    unit_price=25.00,
                    total=1250.00,
                    specifications=[SpecificationItem(name="Grade", value="Grade 5 Ti-6Al-4V")],
                    source_text="Titanium Bolt M10, Qty: 50, Price: $25.00",
                    page_number=1,
                    confidence_level=0.98,
                )
            ],
            commercial_terms=CommercialTermsSchema(
                delivery_time="2 weeks",
                delivery_terms="FOB Houston",
                payment_terms="Net 30",
                warranty="12 Months",
            ),
            evidence=EvidenceCollectionSchema(
                supplier_name=FieldEvidence(extracted_value="Vanguard Fasteners Inc", page_number=1, confidence_level=0.99),
                grand_total=FieldEvidence(extracted_value="1250.00", page_number=1, confidence_level=0.99),
            ),
            overall_confidence=0.98,
        )
        mock_generate.return_value = mock_parsed

        extraction = QuotationExtractionService.extract_from_document(self.document, user=self.user)

        self.assertEqual(extraction.status, ExtractionStatus.COMPLETED)
        self.assertEqual(extraction.supplier_name, "Vanguard Fasteners Inc")
        self.assertEqual(extraction.quotation_number, "QT-VG-9921")
        self.assertEqual(extraction.items_count, 1)
        self.assertEqual(extraction.stated_grand_total, Decimal('1250.00'))
        self.assertTrue(extraction.is_math_consistent)
        self.assertFalse(extraction.is_applied_to_quotation)

    def test_apply_to_quotation(self):
        """Tests applying extracted commercial data and line items to official Quotation."""
        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            supplier_name="Vanguard Fasteners Inc",
            quotation_number="QT-APPLIED-99",
            currency="USD",
            delivery_terms="DDP Chicago",
            payment_terms="Net 60",
            warranty="3 Years",
            stated_subtotal=Decimal('2500.00'),
            stated_grand_total=Decimal('2500.00'),
            extracted_data={
                "line_items": [
                    {
                        "line_number": 1,
                        "description": "Hex Bolt Ti Grade 5",
                        "quantity": 100.0,
                        "unit": "PCS",
                        "unit_price": 25.00,
                        "discount": 0.0,
                        "tax": 0.0,
                        "total": 2500.00,
                        "specifications": [{"name": "Material", "value": "Titanium"}],
                    }
                ]
            },
        )

        updated_quotation = QuotationExtractionService.apply_to_quotation(
            extraction=extraction,
            user=self.user,
            replace_items=True,
        )

        extraction.refresh_from_db()
        self.assertTrue(extraction.is_applied_to_quotation)
        self.assertEqual(extraction.applied_by, self.user)

        # Verify quotation fields updated
        self.assertEqual(updated_quotation.delivery_terms, "DDP Chicago")
        self.assertEqual(updated_quotation.payment_terms, "Net 60")
        self.assertEqual(updated_quotation.subtotal, Decimal('2500.00'))
        self.assertEqual(updated_quotation.total_amount, Decimal('2500.00'))

        # Verify line item created in DB
        items = updated_quotation.items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items[0].description, "Hex Bolt Ti Grade 5")
        self.assertEqual(items[0].quantity, Decimal('100.0000'))
        self.assertEqual(items[0].unit_price, Decimal('25.0000'))


class QuotationExtractionAPITests(APITestCase):
    """API endpoint tests for triggering and retrieving extractions."""

    def setUp(self):
        self.org = Organization.objects.create(name="Global Aerospace", slug="global-aerospace")
        self.user = User.objects.create_user(
            email="lead@globalaerospace.com",
            password="SecurePassword123!",
            first_name="Lead",
            last_name="Buyer",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-API-EXTRACT",
            title="Aerospace Bolts",
            status=RFQStatus.OPEN,
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Apex Aero Ltd",
            contact_person="Sam",
            email="sam@apexaero.com",
            country="United States",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-API-TEST",
            currency="USD",
            created_by=self.user,
        )

        dummy_pdf = b"%PDF-1.4 sample quote"
        uploaded = SimpleUploadedFile("quote_api.pdf", dummy_pdf, content_type="application/pdf")
        self.document = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="quote_api.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(dummy_pdf),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        self.client.force_authenticate(user=self.user)

    @patch('extractions.services.QuotationExtractionService.extract_from_document')
    def test_trigger_extraction_sync(self, mock_extract):
        """Tests POST /api/extractions/document/<id>/?sync=true executes synchronously."""
        mock_extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            supplier_name="Apex Aero Ltd",
            quotation_number="QT-SYNC-01",
            currency="USD",
            stated_grand_total=Decimal('5000.00'),
            items_count=2,
            is_math_consistent=True,
        )
        mock_extract.return_value = mock_extraction

        response = self.client.post(f"/api/extractions/document/{self.document.id}/?sync=true")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['supplier_name'], "Apex Aero Ltd")
        self.assertEqual(response.data['quotation_number'], "QT-SYNC-01")

    @patch('extractions.views.run_ai_extraction_task.delay')
    def test_trigger_extraction_async(self, mock_delay):
        """Tests POST /api/extractions/document/<id>/ returns HTTP 202 Accepted with task info."""
        mock_task = MagicMock()
        mock_task.id = 'async-task-uuid-123'
        mock_delay.return_value = mock_task

        response = self.client.post(f"/api/extractions/document/{self.document.id}/")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertEqual(response.data['task_id'], 'async-task-uuid-123')

    def test_retrieve_extraction_detail(self):
        """Tests GET /api/extractions/<id>/ retrieves extraction record."""
        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            supplier_name="Apex Aero Ltd",
            quotation_number="QT-DETAIL-01",
            currency="USD",
            stated_grand_total=Decimal('7500.00'),
            calculated_grand_total=Decimal('7500.00'),
            is_math_consistent=True,
            items_count=3,
        )

        response = self.client.get(f"/api/extractions/{extraction.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quotation_number'], "QT-DETAIL-01")
        self.assertTrue(response.data['is_math_consistent'])

    def test_tenant_isolation_on_extractions(self):
        """Tests user from another organization cannot retrieve foreign extractions."""
        other_org = Organization.objects.create(name="Rival Space", slug="rival-space")
        other_user = User.objects.create_user(
            email="spy@rivalspace.com",
            password="SecurePassword123!",
            first_name="Rival",
            last_name="Spy",
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            supplier_name="Confidential Aerospace",
        )

        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/extractions/{extraction.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



import copy

from extractions.validation import (
    QuotationCalculator,
    QuotationDeterministicValidator,
    ValidationFlag,
    ValidationReport,
    ValidationSeverity,
    ValidationFlagType,
)


class DeterministicValidationLayerTests(APITestCase):
    """
    Exhaustive tests for the Python Deterministic Validation and Business Calculation Engine.
    Guarantees all 16 business rules, type verifications, calculations, and structured flag generations.
    """

    def setUp(self):
        self.clean_payload = {
            "supplier": {
                "supplier_name": "Apex Precision Instruments LLC",
                "quotation_number": "QUO-2026-9001",
                "contact_person": "Sarah Jenkins",
                "email": "sjenkins@apex.com",
            },
            "quotation": {
                "quotation_date": "2026-11-20",
                "validity_date": "2026-12-20",
                "currency": "USD",
                "subtotal": 1000.00,
                "tax": 100.00,
                "discount": 50.00,
                "shipping": 25.00,
                "grand_total": 1075.00,
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "High Precision Digital Sensor",
                    "model": "HPS-100",
                    "quantity": 10.0,
                    "unit": "PCS",
                    "unit_price": 100.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 1000.00,
                    "specifications": [{"name": "Voltage", "value": "24V"}],
                }
            ],
            "commercial_terms": {
                "payment_terms": "Net 30",
                "delivery_terms": "FOB Austin",
            },
        }

    # 1. Clean Validation Test
    def test_clean_quotation_passes_with_zero_errors(self):
        """Verifies a fully consistent quotation has is_valid=True and has_errors=False."""
        report = QuotationDeterministicValidator.validate(self.clean_payload)
        self.assertTrue(report.is_valid)
        self.assertFalse(report.has_errors)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.calculated_grand_total, Decimal('1075.00'))
        self.assertEqual(report.total_variance, Decimal('0.00'))
        self.assertTrue(report.is_math_consistent)

    # 2. Required Fields Checks
    def test_required_fields_missing_supplier_and_quotation(self):
        """Verifies flag when supplier or quotation blocks are missing."""
        payload = {"line_items": []}
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        self.assertTrue(report.has_errors)
        flags = report.flags_by_field("supplier")
        self.assertTrue(any(f.flag_type == ValidationFlagType.REQUIRED_FIELD_MISSING.value for f in flags))
        quote_flags = report.flags_by_field("quotation")
        self.assertTrue(any(f.flag_type == ValidationFlagType.REQUIRED_FIELD_MISSING.value for f in quote_flags))

    def test_required_fields_empty_line_items(self):
        """Verifies error flag when quotation has 0 line items."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"] = []
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("line_items")
        self.assertTrue(any(f.flag_type == ValidationFlagType.REQUIRED_FIELD_MISSING.value for f in flags))

    def test_required_fields_missing_item_description(self):
        """Verifies error flag when line item description is empty."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"] = [
            {"line_number": 1, "description": "", "quantity": 5.0, "unit": "PCS", "unit_price": 10.0}
        ]
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[0].description")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].flag_type, ValidationFlagType.REQUIRED_FIELD_MISSING.value)
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    # 3. Missing Supplier Checks
    def test_missing_supplier_name(self):
        """Verifies MISSING_SUPPLIER error flag when supplier_name is empty or None."""
        payload = copy.deepcopy(self.clean_payload)
        payload["supplier"] = {"supplier_name": "  ", "quotation_number": "Q-1"}
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("supplier.supplier_name")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].flag_type, ValidationFlagType.MISSING_SUPPLIER.value)
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    # 4. Missing Quotation Number Checks
    def test_missing_quotation_number(self):
        """Verifies MISSING_QUOTATION_NUMBER warning flag when quotation_number is absent."""
        payload = copy.deepcopy(self.clean_payload)
        payload["supplier"] = {"supplier_name": "Apex Precision", "quotation_number": None}
        report = QuotationDeterministicValidator.validate(payload)
        self.assertTrue(report.is_valid)  # Warnings don't make quotation invalid
        self.assertTrue(report.has_warnings)
        flags = report.flags_by_field("supplier.quotation_number")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].flag_type, ValidationFlagType.MISSING_QUOTATION_NUMBER.value)
        self.assertEqual(flags[0].severity, ValidationSeverity.WARNING.value)

    # 5. Invalid Dates Checks
    def test_invalid_date_format(self):
        """Verifies INVALID_DATE_FORMAT error flag for unparseable dates."""
        payload = copy.deepcopy(self.clean_payload)
        payload["quotation"]["quotation_date"] = "2026-02-31"  # Invalid calendar date
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("quotation.quotation_date")
        self.assertTrue(any(f.flag_type == ValidationFlagType.INVALID_DATE_FORMAT.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    def test_date_order_inverted(self):
        """Verifies DATE_ORDER_INVERTED error flag when validity date precedes quotation date."""
        payload = copy.deepcopy(self.clean_payload)
        payload["quotation"]["quotation_date"] = "2026-11-20"
        payload["quotation"]["validity_date"] = "2026-10-15"  # 1 month before issue!
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("quotation.validity_date")
        self.assertTrue(any(f.flag_type == ValidationFlagType.DATE_ORDER_INVERTED.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    def test_date_out_of_range(self):
        """Verifies DATE_OUT_OF_RANGE warning flag for dates far in past or future."""
        payload = copy.deepcopy(self.clean_payload)
        payload["quotation"]["quotation_date"] = "2015-01-01"  # > 5 years ago
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("quotation.quotation_date")
        self.assertTrue(any(f.flag_type == ValidationFlagType.DATE_OUT_OF_RANGE.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.WARNING.value)

    # 6. Negative Quantities Checks
    def test_negative_quantity(self):
        """Verifies NEGATIVE_QUANTITY error flag when quantity < 0."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["quantity"] = -10.0
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("line_items[0].quantity")
        self.assertTrue(any(f.flag_type == ValidationFlagType.NEGATIVE_QUANTITY.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)
        self.assertEqual(flags[0].actual_value, -10.0)

    # 7. Negative Prices Checks
    def test_negative_unit_price_and_negative_total(self):
        """Verifies NEGATIVE_PRICE error flags for negative unit prices and totals."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["unit_price"] = -50.00
        payload["line_items"][0]["total"] = -500.00
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        price_flags = report.flags_by_field("line_items[0].unit_price")
        self.assertTrue(any(f.flag_type == ValidationFlagType.NEGATIVE_PRICE.value for f in price_flags))
        total_flags = report.flags_by_field("line_items[0].total")
        self.assertTrue(any(f.flag_type == ValidationFlagType.NEGATIVE_PRICE.value for f in total_flags))

    def test_negative_header_totals(self):
        """Verifies NEGATIVE_PRICE error flags for negative subtotal and grand total."""
        payload = copy.deepcopy(self.clean_payload)
        payload["quotation"]["subtotal"] = -100.00
        payload["quotation"]["grand_total"] = -150.00
        report = QuotationDeterministicValidator.validate(payload)
        sub_flags = report.flags_by_field("quotation.subtotal")
        self.assertTrue(any(f.flag_type == ValidationFlagType.NEGATIVE_PRICE.value for f in sub_flags))
        grand_flags = report.flags_by_field("quotation.grand_total")
        self.assertTrue(any(f.flag_type == ValidationFlagType.NEGATIVE_PRICE.value for f in grand_flags))

    # 8. Invalid Currencies Checks
    def test_invalid_currency(self):
        """Verifies INVALID_CURRENCY error flag when currency is not recognized ISO 4217 code."""
        payload = copy.deepcopy(self.clean_payload)
        payload["quotation"]["currency"] = "FAKE_CURRENCY_123"
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("quotation.currency")
        self.assertTrue(any(f.flag_type == ValidationFlagType.INVALID_CURRENCY.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    # 9. Quantity Inconsistencies Checks
    def test_quantity_inconsistency_zero_quantity(self):
        """Verifies QUANTITY_INCONSISTENCY error flag when quantity is 0."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["quantity"] = 0.0
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("line_items[0].quantity")
        self.assertTrue(any(f.flag_type == ValidationFlagType.QUANTITY_INCONSISTENCY.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    def test_quantity_inconsistency_fractional_discrete_unit(self):
        """Verifies QUANTITY_INCONSISTENCY warning flag for fractional quantities on discrete units."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["unit"] = "PCS"
        payload["line_items"][0]["quantity"] = 2.5
        payload["line_items"][0]["total"] = 250.00
        payload["quotation"]["subtotal"] = 250.00
        payload["quotation"]["grand_total"] = 325.00
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[0].quantity")
        self.assertTrue(any(f.flag_type == ValidationFlagType.QUANTITY_INCONSISTENCY.value for f in flags))
        self.assertTrue(any(f.severity == ValidationSeverity.WARNING.value for f in flags))

    # 10. Incorrect Line Totals Checks
    def test_incorrect_line_totals(self):
        """Verifies INCORRECT_LINE_TOTAL error flag when stated line total differs from qty * price."""
        payload = copy.deepcopy(self.clean_payload)
        # Expected: 10 * 100 - 0 + 0 = 1000.00. We state: 1250.00
        payload["line_items"][0]["total"] = 1250.00
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        self.assertFalse(report.is_math_consistent)
        flags = report.flags_by_field("line_items[0].total")
        self.assertTrue(any(f.flag_type == ValidationFlagType.INCORRECT_LINE_TOTAL.value for f in flags))
        self.assertEqual(flags[0].expected_value, 1000.00)
        self.assertEqual(flags[0].actual_value, 1250.00)

    # 11. Subtotal Inconsistencies Checks
    def test_subtotal_inconsistency(self):
        """Verifies SUBTOTAL_INCONSISTENCY error flag when stated subtotal differs from sum of line items."""
        payload = copy.deepcopy(self.clean_payload)
        # Line item subtotal is 1000.00. We state subtotal: 1200.00
        payload["quotation"]["subtotal"] = 1200.00
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        self.assertFalse(report.is_math_consistent)
        flags = report.flags_by_field("quotation.subtotal")
        self.assertTrue(any(f.flag_type == ValidationFlagType.SUBTOTAL_INCONSISTENCY.value for f in flags))
        self.assertEqual(flags[0].expected_value, 1000.00)
        self.assertEqual(flags[0].actual_value, 1200.00)

    # 12. Tax Calculation Inconsistencies Checks
    def test_tax_calculation_inconsistency_itemized_mismatch(self):
        """Verifies TAX_CALCULATION_INCONSISTENCY error flag when stated tax differs from sum of line taxes."""
        payload = copy.deepcopy(self.clean_payload)
        # Item specifies tax=10.00. We state header tax=100.00
        payload["line_items"][0]["tax"] = 10.00
        payload["quotation"]["tax"] = 100.00
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("quotation.tax")
        self.assertTrue(any(f.flag_type == ValidationFlagType.TAX_CALCULATION_INCONSISTENCY.value for f in flags))
        self.assertEqual(flags[0].expected_value, 10.00)
        self.assertEqual(flags[0].actual_value, 100.00)

    def test_tax_calculation_inconsistency_excessive_tax(self):
        """Verifies TAX_CALCULATION_INCONSISTENCY warning when tax exceeds the subtotal."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["tax"] = None
        payload["quotation"]["subtotal"] = 50.00
        payload["quotation"]["tax"] = 100.00  # Tax > Subtotal!
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("quotation.tax")
        self.assertTrue(any(f.flag_type == ValidationFlagType.TAX_CALCULATION_INCONSISTENCY.value for f in flags))
        self.assertTrue(any(f.severity == ValidationSeverity.WARNING.value for f in flags))

    # 13. Grand Total Inconsistencies Checks
    def test_grand_total_inconsistency(self):
        """Verifies GRAND_TOTAL_INCONSISTENCY error flag when stated grand total doesn't reconcile."""
        payload = copy.deepcopy(self.clean_payload)
        # Expected: 1000 - 50 + 100 + 25 = 1075.00. We state: 2000.00
        payload["quotation"]["grand_total"] = 2000.00
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        self.assertFalse(report.is_math_consistent)
        self.assertEqual(report.total_variance, Decimal('925.00'))
        flags = report.flags_by_field("quotation.grand_total")
        self.assertTrue(any(f.flag_type == ValidationFlagType.GRAND_TOTAL_INCONSISTENCY.value for f in flags))
        self.assertEqual(flags[0].expected_value, 1075.00)
        self.assertEqual(flags[0].actual_value, 2000.00)

    # 14. Duplicate Items Checks
    def test_duplicate_items_by_model(self):
        """Verifies DUPLICATE_ITEM warning flag when same model number appears multiple times."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"] = [
            {
                "line_number": 1,
                "description": "Widget Model 42",
                "model": "WM-42",
                "quantity": 1.0,
                "unit": "PCS",
                "unit_price": 50.00,
                "total": 50.00,
            },
            {
                "line_number": 2,
                "description": "Widget Model 42 Spare",
                "model": "wm-42",  # Duplicate case-insensitive
                "quantity": 1.0,
                "unit": "PCS",
                "unit_price": 50.00,
                "total": 50.00,
            },
        ]
        payload["quotation"]["subtotal"] = 100.00
        payload["quotation"]["grand_total"] = 175.00
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[1].model")
        self.assertTrue(any(f.flag_type == ValidationFlagType.DUPLICATE_ITEM.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.WARNING.value)

    def test_duplicate_items_by_description(self):
        """Verifies DUPLICATE_ITEM warning flag when same description appears without distinct models."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"] = [
            {
                "line_number": 1,
                "description": "Identical Industrial Bracket",
                "quantity": 1.0,
                "unit": "PCS",
                "unit_price": 50.00,
                "total": 50.00,
            },
            {
                "line_number": 2,
                "description": "Identical Industrial Bracket",
                "quantity": 2.0,
                "unit": "PCS",
                "unit_price": 50.00,
                "total": 100.00,
            },
        ]
        payload["quotation"]["subtotal"] = 150.00
        payload["quotation"]["grand_total"] = 225.00
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[1].description")
        self.assertTrue(any(f.flag_type == ValidationFlagType.DUPLICATE_ITEM.value for f in flags))

    # 15. Missing Units Checks
    def test_missing_units(self):
        """Verifies MISSING_UNIT warning flag when line item lacks unit of measurement."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["unit"] = None
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[0].unit")
        self.assertTrue(any(f.flag_type == ValidationFlagType.MISSING_UNIT.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.WARNING.value)

    # 16. Missing Specifications Checks
    def test_missing_specifications(self):
        """Verifies MISSING_SPECIFICATIONS info flag when line item lacks specifications."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["specifications"] = []
        report = QuotationDeterministicValidator.validate(payload)
        flags = report.flags_by_field("line_items[0].specifications")
        self.assertTrue(any(f.flag_type == ValidationFlagType.MISSING_SPECIFICATIONS.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.INFO.value)

    # 17. Invalid Data Types Checks
    def test_invalid_data_types_string_for_numeric(self):
        """Verifies INVALID_DATA_TYPE error flag when non-numeric string is passed for float fields."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["quantity"] = "five_pcs"
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("line_items[0].quantity")
        self.assertTrue(any(f.flag_type == ValidationFlagType.INVALID_DATA_TYPE.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    def test_invalid_data_types_boolean_for_numeric(self):
        """Verifies INVALID_DATA_TYPE error flag when boolean is passed for quantity or price."""
        payload = copy.deepcopy(self.clean_payload)
        payload["line_items"][0]["unit_price"] = True  # In Python, True is an int subclass!
        report = QuotationDeterministicValidator.validate(payload)
        self.assertFalse(report.is_valid)
        flags = report.flags_by_field("line_items[0].unit_price")
        self.assertTrue(any(f.flag_type == ValidationFlagType.INVALID_DATA_TYPE.value for f in flags))
        self.assertEqual(flags[0].severity, ValidationSeverity.ERROR.value)

    # 18. Pure Python Calculator Precision Tests
    def test_calculator_precision_and_currency_stripping(self):
        """Verifies QuotationCalculator strips currency symbols, handles half-up rounding, and Decimal precision."""
        self.assertEqual(QuotationCalculator.to_decimal("$1,234.56"), Decimal('1234.56'))
        self.assertEqual(QuotationCalculator.to_decimal(10.555), Decimal('10.56'))
        self.assertIsNone(QuotationCalculator.to_decimal("invalid"))
        self.assertIsNone(QuotationCalculator.to_decimal(None))

        line_tot = QuotationCalculator.calculate_line_total(
            quantity=Decimal('3.00'),
            unit_price=Decimal('15.50'),
            discount=Decimal('2.50'),
            tax=Decimal('1.25'),
        )
        # (3 * 15.50) - 2.50 + 1.25 = 46.50 - 2.50 + 1.25 = 45.25
        self.assertEqual(line_tot, Decimal('45.25'))

    # 19. Report Serialization & Filtering Tests
    def test_validation_report_serialization_and_methods(self):
        """Verifies ValidationReport to_dict, severity filters, and counts."""
        report = ValidationReport()
        report.add_flag(ValidationFlag(
            flag_type=ValidationFlagType.MISSING_SUPPLIER.value,
            severity=ValidationSeverity.ERROR.value,
            field="supplier.supplier_name",
            explanation="Supplier missing",
        ))
        report.add_flag(ValidationFlag(
            flag_type=ValidationFlagType.MISSING_UNIT.value,
            severity=ValidationSeverity.WARNING.value,
            field="line_items[0].unit",
            explanation="Unit missing",
        ))
        report.add_flag(ValidationFlag(
            flag_type=ValidationFlagType.MISSING_SPECIFICATIONS.value,
            severity=ValidationSeverity.INFO.value,
            field="line_items[0].specifications",
            explanation="Specs missing",
        ))

        self.assertFalse(report.is_valid)
        self.assertTrue(report.has_errors)
        self.assertTrue(report.has_warnings)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.warning_count, 1)
        self.assertEqual(report.info_count, 1)

        dict_repr = report.to_dict()
        self.assertEqual(dict_repr["error_count"], 1)
        self.assertEqual(len(dict_repr["flags"]), 3)
        self.assertEqual(dict_repr["flags"][0]["flag_type"], ValidationFlagType.MISSING_SUPPLIER.value)



from extractions.models import ReviewStatus, CorrectionType, QuotationExtractionCorrection
from extractions.services import QuotationReviewService


class HumanReviewWorkflowAPITests(APITestCase):
    """
    Automated integration test suite for the Quotation Extraction Human-Review Workflow.
    Verifies human corrections, audit history tracking, field review marking,
    distinction between unreviewed AI and approved data, and multi-tier permissions.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="AeroDynamics Corp", slug="aerodynamics-corp")
        
        # 1. Procurement Manager (has review & approval permissions)
        self.manager = User.objects.create_user(
            email="manager@aerodynamics.com",
            password="SecurePassword123!",
            first_name="Procurement",
            last_name="Manager",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.manager,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        # 2. Regular Procurement User (can review/correct, but CANNOT approve)
        self.buyer = User.objects.create_user(
            email="buyer@aerodynamics.com",
            password="SecurePassword123!",
            first_name="Junior",
            last_name="Buyer",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.buyer,
            role=OrganizationRole.PROCUREMENT_USER,
        )

        # 3. Target RFQ, Supplier & Quotation
        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-REV-01",
            title="Titanium Structural Bolts",
            status=RFQStatus.OPEN,
            created_by=self.manager,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Titanium Fasteners Ltd",
            contact_person="Bob Smith",
            email="bob@titaniumfasteners.com",
            country="United States",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-REV-100",
            currency="USD",
            created_by=self.manager,
        )

        dummy_pdf = b"%PDF-1.4 sample quote"
        uploaded = SimpleUploadedFile("quote.pdf", dummy_pdf, content_type="application/pdf")
        self.document = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="quote.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(dummy_pdf),
            mime_type="application/pdf",
            uploaded_by=self.manager,
        )

        # Initial raw AI extraction state (with an initial typo / discrepancy to be corrected)
        self.initial_data = {
            "supplier": {
                "supplier_name": "Titanium Fasteners Ltd (OCR Typo)",
                "quotation_number": "QT-REV-100-AI",
                "contact_person": "Bob Smith",
                "email": "bob@titaniumfasteners.com",
                "phone": "+1-555-0100",
                "address": "100 Industrial Road, Dallas, TX",
            },
            "quotation": {
                "quotation_date": "2026-11-20",
                "validity_date": "2026-12-20",
                "currency": "USD",
                "subtotal": 5000.00,
                "tax": 500.00,
                "discount": 0.00,
                "shipping": 100.00,
                "grand_total": 5600.00,
            },
            "line_items": [
                {
                    "line_number": 1,
                    "description": "Grade 5 Titanium Bolt M12x60",
                    "model": "TB-M12-60",
                    "quantity": 100.0,
                    "unit": "PCS",
                    "unit_price": 50.00,
                    "discount": 0.00,
                    "tax": 0.00,
                    "total": 5000.00,
                    "specifications": [{"name": "Material", "value": "Ti-6Al-4V"}],
                }
            ],
            "commercial_terms": {
                "delivery_time": "4 weeks",
                "delivery_terms": "FOB Dallas",
                "payment_terms": "Net 30",
                "warranty": "12 Months",
                "notes": "Original AI extracted terms.",
            },
            "overall_confidence": 0.95,
        }

        self.extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            review_status=ReviewStatus.UNREVIEWED,
            is_approved=False,
            supplier_name="Titanium Fasteners Ltd (OCR Typo)",
            quotation_number="QT-REV-100-AI",
            currency="USD",
            stated_subtotal=Decimal('5000.00'),
            stated_grand_total=Decimal('5600.00'),
            calculated_items_subtotal=Decimal('5000.00'),
            calculated_grand_total=Decimal('5600.00'),
            is_math_consistent=True,
            items_count=1,
            extracted_data=copy.deepcopy(self.initial_data),
            original_extracted_data=copy.deepcopy(self.initial_data),
        )

    # 1. View Extracted Data & Validation Flags
    def test_view_extracted_data_and_validation_flags(self):
        """Tests that GET /api/extractions/<id>/ returns extraction data, review status, and validation flags."""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(f"/api/extractions/{self.extraction.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['review_status'], ReviewStatus.UNREVIEWED)
        self.assertFalse(response.data['is_approved'])
        self.assertIn('extracted_data', response.data)
        self.assertIn('validation_flags', response.data)
        self.assertIn('recent_corrections', response.data)

    # 2. Correct Supplier Information
    def test_correct_supplier_information_creates_audit_log(self):
        """Tests correcting supplier name and quotation number logs audit entries and updates state."""
        self.client.force_authenticate(user=self.buyer)
        payload = {
            "supplier": {
                "supplier_name": "Titanium Fasteners Inc (Corrected)",
                "quotation_number": "QUO-OFFICIAL-2026",
            },
            "reason": "Fix OCR spelling on legal company name",
            "mark_reviewed": True,
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/correct/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertEqual(self.extraction.supplier_name, "Titanium Fasteners Inc (Corrected)")
        self.assertEqual(self.extraction.quotation_number, "QUO-OFFICIAL-2026")
        self.assertEqual(self.extraction.review_status, ReviewStatus.IN_REVIEW)
        self.assertEqual(self.extraction.reviewed_by, self.buyer)
        self.assertTrue(self.extraction.has_human_corrections)
        self.assertIn("supplier.supplier_name", self.extraction.reviewed_fields)

        # Verify audit history
        corrections = QuotationExtractionCorrection.objects.filter(extraction=self.extraction)
        self.assertEqual(corrections.count(), 2)
        name_corr = corrections.get(field_path="supplier.supplier_name")
        self.assertEqual(name_corr.correction_type, CorrectionType.SUPPLIER)
        self.assertEqual(name_corr.previous_value, "Titanium Fasteners Ltd (OCR Typo)")
        self.assertEqual(name_corr.new_value, "Titanium Fasteners Inc (Corrected)")
        self.assertEqual(name_corr.corrected_by, self.buyer)

    # 3. Correct Quotation Information & Financials
    def test_correct_quotation_information_recalculates_deterministic_totals(self):
        """Tests correcting tax and subtotal recalculates grand total and logs tax_shipping correction."""
        self.client.force_authenticate(user=self.buyer)
        payload = {
            "quotation": {
                "tax": 250.00,  # Reduced from 500 to 250
                "grand_total": 5350.00,  # 5000 + 250 + 100 = 5350
            },
            "reason": "Adjust tax calculation per tax exemption cert",
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/correct/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertEqual(self.extraction.stated_tax, Decimal('250.00'))
        self.assertEqual(self.extraction.stated_grand_total, Decimal('5350.00'))
        self.assertEqual(self.extraction.calculated_grand_total, Decimal('5350.00'))
        self.assertTrue(self.extraction.is_math_consistent)

        tax_corr = QuotationExtractionCorrection.objects.get(
            extraction=self.extraction,
            field_path="quotation.tax",
        )
        self.assertEqual(tax_corr.correction_type, CorrectionType.TAX_SHIPPING)
        self.assertEqual(tax_corr.previous_value, 500.00)
        self.assertEqual(tax_corr.new_value, 250.00)

    # 4. Correct Line Item Prices, Quantities, and Specifications
    def test_correct_line_item_price_quantity_specifications(self):
        """Tests correcting line item price, quantity, and specs creates specific audit logs and updates math."""
        self.client.force_authenticate(user=self.buyer)
        updated_items = [
            {
                "line_number": 1,
                "description": "Grade 5 Titanium Bolt M12x60 (High Tensile)",
                "model": "TB-M12-60",
                "quantity": 120.0,  # Changed from 100 to 120
                "unit": "PCS",
                "unit_price": 45.00,  # Changed from 50.00 to 45.00 (Volume discount!)
                "discount": 0.00,
                "tax": 0.00,
                "total": 5400.00,  # 120 * 45 = 5400.00
                "specifications": [
                    {"name": "Material", "value": "Ti-6Al-4V Grade 5"},
                    {"name": "Tensile Strength", "value": "950 MPa"},
                ],
            }
        ]
        payload = {
            "quotation": {
                "subtotal": 5400.00,
                "tax": 540.00,
                "shipping": 100.00,
                "grand_total": 6040.00,
            },
            "line_items": updated_items,
            "reason": "Applied volume discount agreed with vendor rep",
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/correct/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertEqual(self.extraction.calculated_items_subtotal, Decimal('5400.00'))
        self.assertEqual(self.extraction.calculated_grand_total, Decimal('6040.00'))
        self.assertTrue(self.extraction.is_math_consistent)

        # Check price correction audit log
        price_corr = QuotationExtractionCorrection.objects.get(
            extraction=self.extraction,
            field_path="line_items[0].unit_price",
        )
        self.assertEqual(price_corr.correction_type, CorrectionType.PRICE)
        self.assertEqual(price_corr.previous_value, 50.00)
        self.assertEqual(price_corr.new_value, 45.00)

        # Check quantity correction audit log
        qty_corr = QuotationExtractionCorrection.objects.get(
            extraction=self.extraction,
            field_path="line_items[0].quantity",
        )
        self.assertEqual(qty_corr.correction_type, CorrectionType.QUANTITY)
        self.assertEqual(qty_corr.previous_value, 100.0)
        self.assertEqual(qty_corr.new_value, 120.0)

        # Check specifications correction audit log
        spec_corr = QuotationExtractionCorrection.objects.get(
            extraction=self.extraction,
            field_path="line_items[0].specifications",
        )
        self.assertEqual(spec_corr.correction_type, CorrectionType.SPECIFICATION)

    # 5. Correct Commercial Terms
    def test_correct_commercial_terms(self):
        """Tests updating commercial delivery, payment, and warranty terms."""
        self.client.force_authenticate(user=self.buyer)
        payload = {
            "commercial_terms": {
                "payment_terms": "Net 60 Days",
                "warranty": "24 Months Manufacturer",
            },
            "reason": "Updated to corporate standard terms",
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/correct/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertEqual(self.extraction.payment_terms, "Net 60 Days")
        self.assertEqual(self.extraction.warranty, "24 Months Manufacturer")

        term_corr = QuotationExtractionCorrection.objects.get(
            extraction=self.extraction,
            field_path="commercial_terms.payment_terms",
        )
        self.assertEqual(term_corr.correction_type, CorrectionType.COMMERCIAL_TERMS)
        self.assertEqual(term_corr.previous_value, "Net 30")
        self.assertEqual(term_corr.new_value, "Net 60 Days")

    # 6. Mark Fields as Reviewed
    def test_mark_fields_as_reviewed(self):
        """Tests POST /api/extractions/<id>/mark-reviewed/ adds fields to reviewed_fields."""
        self.client.force_authenticate(user=self.buyer)
        payload = {
            "fields": [
                "supplier.supplier_name",
                "quotation.grand_total",
                "line_items[0].specifications",
            ]
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/mark-reviewed/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertIn("supplier.supplier_name", self.extraction.reviewed_fields)
        self.assertIn("quotation.grand_total", self.extraction.reviewed_fields)
        self.assertEqual(self.extraction.reviewed_by, self.buyer)
        self.assertIsNotNone(self.extraction.reviewed_at)

    # 7. Approve Extraction (Procurement Manager Permission)
    def test_approve_extraction_by_procurement_manager(self):
        """Tests procurement manager can approve extraction, setting review_status=APPROVED."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "review_notes": "All line items, specifications, and payment terms approved.",
            "apply_to_quotation": False,
        }
        response = self.client.post(f"/api/extractions/{self.extraction.id}/approve/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertTrue(self.extraction.is_approved)
        self.assertEqual(self.extraction.review_status, ReviewStatus.APPROVED)
        self.assertEqual(self.extraction.approved_by, self.manager)
        self.assertIsNotNone(self.extraction.approved_at)
        self.assertEqual(self.extraction.review_notes, "All line items, specifications, and payment terms approved.")

    # 8. Regular Buyer Cannot Approve (Permission Check)
    def test_approve_extraction_denied_for_regular_procurement_user(self):
        """Tests regular buyer without Manager role receives HTTP 403 Forbidden on approve."""
        self.client.force_authenticate(user=self.buyer)
        payload = {"review_notes": "Attempting unauthorized approval"}
        response = self.client.post(f"/api/extractions/{self.extraction.id}/approve/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.extraction.refresh_from_db()
        self.assertFalse(self.extraction.is_approved)
        self.assertEqual(self.extraction.review_status, ReviewStatus.UNREVIEWED)

    # 9. Reject Extraction
    def test_reject_extraction(self):
        """Tests rejecting an extraction with reason."""
        self.client.force_authenticate(user=self.buyer)
        payload = {"reason": "Document is an expired quote from 2024. Resubmission required."}
        response = self.client.post(f"/api/extractions/{self.extraction.id}/reject/", payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.extraction.refresh_from_db()
        self.assertFalse(self.extraction.is_approved)
        self.assertEqual(self.extraction.review_status, ReviewStatus.REJECTED)
        self.assertEqual(self.extraction.review_notes, "Document is an expired quote from 2024. Resubmission required.")
        self.assertEqual(self.extraction.reviewed_by, self.buyer)

    # 10. Distinguish Approved Data from Unreviewed AI Data
    def test_distinguish_approved_data_from_unreviewed_ai_data(self):
        """Tests that original AI data remains pristine while working data reflects human review."""
        self.client.force_authenticate(user=self.buyer)
        # Apply human correction
        self.client.post(
            f"/api/extractions/{self.extraction.id}/correct/",
            {"supplier": {"supplier_name": "Titanium Verified Corp"}},
            format='json',
        )

        response = self.client.get(f"/api/extractions/{self.extraction.id}/original-data/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_human_corrections'])
        self.assertEqual(response.data['corrections_count'], 1)
        # Original AI snapshot has old name
        self.assertEqual(
            response.data['original_extracted_data']['supplier']['supplier_name'],
            "Titanium Fasteners Ltd (OCR Typo)",
        )
        # Working verified data has new name
        self.assertEqual(
            response.data['current_working_data']['supplier']['supplier_name'],
            "Titanium Verified Corp",
        )

    # 11. Apply Approved Extraction with Human Corrections to Quotation
    def test_apply_approved_corrected_extraction_to_quotation(self):
        """Tests that applying an extraction syncs the human-corrected data into QuotationItem."""
        self.client.force_authenticate(user=self.manager)

        # 1. Human corrects line item price to $42.50
        self.client.post(
            f"/api/extractions/{self.extraction.id}/correct/",
            {
                "line_items": [
                    {
                        "line_number": 1,
                        "description": "Grade 5 Titanium Bolt M12x60",
                        "quantity": 100.0,
                        "unit": "PCS",
                        "unit_price": 42.50,  # Corrected price
                        "total": 4250.00,
                        "specifications": [{"name": "Material", "value": "Ti-6Al-4V"}],
                    }
                ],
                "quotation": {
                    "subtotal": 4250.00,
                    "tax": 0.00,
                    "shipping": 0.00,
                    "discount": 0.00,
                    "grand_total": 4250.00,
                },
            },
            format='json',
        )

        # 2. Approve and apply
        approve_resp = self.client.post(
            f"/api/extractions/{self.extraction.id}/approve/",
            {"apply_to_quotation": True, "review_notes": "Approved and synced."},
            format='json',
        )
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)

        # 3. Verify QuotationItem reflects human-corrected price, NOT AI unreviewed price
        self.quotation.refresh_from_db()
        items = list(self.quotation.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].unit_price, Decimal('42.5000'))
        self.assertEqual(self.quotation.subtotal, Decimal('4250.00'))

    # 12. Audit History Endpoint
    def test_audit_history_endpoint_lists_all_changes(self):
        """Tests GET /api/extractions/<id>/audit-history/ returns all chronologically logged corrections."""
        self.client.force_authenticate(user=self.buyer)
        self.client.post(
            f"/api/extractions/{self.extraction.id}/correct/",
            {
                "supplier": {"supplier_name": "New Supplier Name"},
                "quotation": {"currency": "EUR"},
            },
            format='json',
        )

        response = self.client.get(f"/api/extractions/{self.extraction.id}/audit-history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['corrections_count'], 2)
        corrections = response.data['corrections']
        self.assertEqual(len(corrections), 2)
        paths = [c['field_path'] for c in corrections]
        self.assertIn("supplier.supplier_name", paths)
        self.assertIn("quotation.currency", paths)
