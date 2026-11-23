"""
Automated tests for Document Processing and Text Extraction in QuoteFlow AI.
Tests PDF extraction (PyMuPDF), Excel extraction (openpyxl),
scanned/low-text detection, service orchestration, database persistence, and API endpoints.
"""

import io
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import openpyxl

from organizations.models import Organization, OrganizationMembership, OrganizationRole
from rfqs.models import RFQ, RFQStatus
from suppliers.models import Supplier
from users.models import User
from quotations.models import (
    Quotation,
    QuotationDocument,
    DocumentFileType,
    DocumentProcessingStatus,
    DocumentExtractionResult,
)
from quotations.processing import (
    PDFExtractor,
    ExcelExtractor,
    ImageExtractor,
    OCREngine,
    DocumentProcessingService,
    DocumentExtractionResult as DTOExtractionResult,
    CorruptDocumentError,
    EmptyDocumentError,
    UnsupportedDocumentFormatError,
    TesseractNotInstalledError,
)


def create_sample_pdf_bytes(pages_content: list[str]) -> bytes:
    """Helper creating an in-memory PDF with the specified text for each page using PyMuPDF."""
    doc = fitz.open()
    for page_text in pages_content:
        page = doc.new_page(width=595, height=842)  # A4 size
        if page_text:
            # Insert text at top of page (x=50, y=72)
            page.insert_text(fitz.Point(50, 72), page_text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_excel_bytes(sheets_data: dict[str, list[list]]) -> bytes:
    """Helper creating an in-memory XLSX workbook with multiple sheets and cell types using openpyxl."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    for sheet_name, rows in sheets_data.items():
        ws = wb.create_sheet(title=sheet_name)
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, val in enumerate(row, start=1):
                ws.cell(row=row_idx, column=col_idx, value=val)

    stream = io.BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


class PDFExtractorTests(APITestCase):
    """Unit tests for PDFExtractor using PyMuPDF."""

    def test_extract_multipage_text_pdf(self):
        """Tests page-by-page extraction, page number preservation, and word counts from a multi-page PDF."""
        page_1 = "QUOTATION: QT-2026-901\nSupplier: Aero Precision Inc.\nDate: 2026-11-20\nCurrency: USD"
        page_2 = "Line 1: Titanium Hex Flange Bolt, Qty: 200, Unit Price: $14.50, Total: $2,900.00\nLine 2: High Temp Gasket, Qty: 50, Unit Price: $8.00, Total: $400.00"
        page_3 = "Commercial Terms:\nPayment Terms: Net 30\nDelivery Lead Time: 3 Calendar Weeks\nIncoterms: DDP Chicago\nWarranty: 24 Months"

        pdf_bytes = create_sample_pdf_bytes([page_1, page_2, page_3])
        extractor = PDFExtractor()
        result = extractor.extract(pdf_bytes)

        self.assertEqual(result.document_type, 'pdf')
        self.assertEqual(result.total_units, 3)
        self.assertEqual(len(result.pages), 3)

        # Verify page numbers and ordering
        self.assertEqual(result.pages[0].page_number, 1)
        self.assertEqual(result.pages[1].page_number, 2)
        self.assertEqual(result.pages[2].page_number, 3)

        # Verify text content per page
        self.assertIn("Aero Precision Inc.", result.pages[0].text)
        self.assertIn("Titanium Hex Flange Bolt", result.pages[1].text)
        self.assertIn("Net 30", result.pages[2].text)

        # Verify word and character counts
        self.assertGreater(result.character_count, 150)
        self.assertGreater(result.word_count, 25)
        self.assertTrue(result.has_extractable_text)
        self.assertFalse(result.is_scanned_or_low_text)
        self.assertIsNone(result.low_text_reason)

        # Verify raw text contains all pages
        self.assertIn("--- Page 1 of 3 ---", result.raw_text)
        self.assertIn("--- Page 2 of 3 ---", result.raw_text)
        self.assertIn("--- Page 3 of 3 ---", result.raw_text)

    def test_detect_scanned_or_low_text_pdf(self):
        """Tests detection and flagging of PDFs with little or no extractable digital text (e.g. scanned image PDFs)."""
        # Create a 2-page PDF with zero text (e.g. empty or scanned mock)
        pdf_bytes = create_sample_pdf_bytes(["", ""])
        extractor = PDFExtractor()
        result = extractor.extract(pdf_bytes)

        self.assertEqual(result.total_units, 2)
        self.assertEqual(result.character_count, 0)
        self.assertFalse(result.has_extractable_text)
        self.assertTrue(result.is_scanned_or_low_text)
        self.assertIsNotNone(result.low_text_reason)
        self.assertIn("scanned image", result.low_text_reason.lower())
        self.assertTrue(any("low text" in w.lower() for w in result.warnings))

    def test_corrupt_pdf_raises_error(self):
        """Tests that invalid/corrupted bytes raise CorruptDocumentError."""
        extractor = PDFExtractor()
        with self.assertRaises(CorruptDocumentError):
            extractor.extract(b"Not a valid PDF file stream")

    def test_empty_pdf_raises_error(self):
        """Tests that a 0-byte source raises EmptyDocumentError."""
        extractor = PDFExtractor()
        with self.assertRaises(EmptyDocumentError):
            extractor.extract(b"")


class ExcelExtractorTests(APITestCase):
    """Unit tests for ExcelExtractor using openpyxl."""

    def test_extract_multisheet_excel(self):
        """Tests multi-worksheet extraction, sheet names, cell formatting, and tabular markdown."""
        sheets = {
            "Quote Summary": [
                ["Field", "Value"],
                ["Quotation Ref", "QT-EXCEL-001"],
                ["Supplier", "Precision Valve Corp"],
                ["Quotation Date", date(2026, 11, 21)],
                ["Payment Terms", "Net 45 Days"],
                [None, None],  # empty row to test empty row filtering
            ],
            "Line Items": [
                ["Item #", "Part Name", "Qty", "Unit", "Unit Price", "Total"],
                [1, "Hydraulic Seal", 100, "EA", 12.50, 1250.00],
                [2, "Check Valve", 20, "EA", 145.00, 2900.00],
                [3, "O-Ring Kit", None, "SET", 35.00, None],  # empty cells within row
                ["", "", "", "", "", ""],  # empty row
            ],
            "Commercial Terms": [
                ["Terms Description", "Clause"],
                ["Warranty", "36 Months Standard Warranty"],
                ["Delivery", "FOB Destination (4 weeks)"],
            ]
        }

        xlsx_bytes = create_sample_excel_bytes(sheets)
        extractor = ExcelExtractor()
        result = extractor.extract(xlsx_bytes)

        self.assertEqual(result.document_type, 'excel')
        self.assertEqual(result.total_units, 3)
        self.assertEqual(len(result.sheets), 3)

        # Check sheet names
        sheet_names = [s.sheet_name for s in result.sheets]
        self.assertEqual(sheet_names, ["Quote Summary", "Line Items", "Commercial Terms"])

        # Check Line Items worksheet extraction
        line_items_sheet = result.sheets[1]
        self.assertEqual(line_items_sheet.sheet_name, "Line Items")
        self.assertEqual(line_items_sheet.headers, ["Item #", "Part Name", "Qty", "Unit", "Unit Price", "Total"])
        self.assertGreater(line_items_sheet.non_empty_rows, 0)
        self.assertTrue(line_items_sheet.has_data)

        # Check Markdown table structure
        self.assertIn("| Item # | Part Name | Qty | Unit | Unit Price | Total |", line_items_sheet.table_markdown)
        self.assertIn("Hydraulic Seal", line_items_sheet.table_markdown)

        # Check date cell formatting in Quote Summary sheet
        summary_sheet = result.sheets[0]
        self.assertIn("2026-11-21", summary_sheet.table_markdown)

        # Check overall metrics
        self.assertTrue(result.has_extractable_text)
        self.assertFalse(result.is_scanned_or_low_text)
        self.assertGreater(result.word_count, 30)

    def test_empty_excel_workbook(self):
        """Tests that a blank Excel sheet is flagged as empty / low text."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EmptySheet"
        stream = io.BytesIO()
        wb.save(stream)
        wb.close()

        extractor = ExcelExtractor()
        result = extractor.extract(stream.getvalue())

        self.assertEqual(result.total_units, 1)
        self.assertFalse(result.has_extractable_text)
        self.assertTrue(result.is_scanned_or_low_text)
        self.assertIn("no non-empty rows", result.low_text_reason.lower())

    def test_corrupt_excel_raises_error(self):
        """Tests that invalid bytes raise CorruptDocumentError."""
        extractor = ExcelExtractor()
        with self.assertRaises(CorruptDocumentError):
            extractor.extract(b"Not a valid Excel XLSX archive")


class DocumentProcessingServiceIntegrationTests(APITestCase):
    """Integration tests for DocumentProcessingService with the database and models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='extractor@quoteflow.ai',
            password='Password123!',
            first_name='Document',
            last_name='Tester',
        )
        self.org = Organization.objects.create(name='Extraction Org', slug='extraction-org')
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role=OrganizationRole.ADMIN)

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-DOC-001',
            title='Valves & Seals RFQ',
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Apex Machining',
            email='apex@example.com',
            contact_person='Bob Smith',
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='QT-TEST-DOC',
            currency='USD',
            created_by=self.user,
        )

    def test_process_quotation_document_pdf(self):
        """Tests end-to-end processing and DB persistence for an uploaded PDF."""
        pdf_bytes = create_sample_pdf_bytes([
            "Apex Machining Quotation\nItem: Titanium Rod\nPrice: $120.00",
            "Terms: Net 30, Delivery: 2 Weeks"
        ])
        uploaded_file = SimpleUploadedFile("quote.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded_file,
            original_filename="quote.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            checksum_sha256="abc123hash",
            uploaded_by=self.user,
        )

        # Process document through the service
        result = DocumentProcessingService.process_quotation_document(doc)

        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.COMPLETED)
        self.assertEqual(doc.processing_progress, 100)
        self.assertEqual(doc.processing_error, "")

        # Verify DocumentExtractionResult database model record
        self.assertTrue(hasattr(doc, 'extraction_result'))
        extraction = doc.extraction_result
        self.assertEqual(extraction.document_type, 'pdf')
        self.assertEqual(extraction.pages_or_sheets_count, 2)
        self.assertIn("Titanium Rod", extraction.raw_text)
        self.assertIn("Net 30", extraction.raw_text)
        self.assertGreater(extraction.character_count, 50)
        self.assertFalse(extraction.is_scanned_or_low_text)
        self.assertEqual(extraction.organization, self.org)

    def test_process_quotation_document_excel(self):
        """Tests end-to-end processing and DB persistence for an uploaded Excel spreadsheet."""
        sheets = {
            "Bids": [
                ["Part Number", "Description", "Price"],
                ["PN-101", "Gasket Kit", 45.00],
                ["PN-102", "O-Ring Seal", 12.50],
            ]
        }
        xlsx_bytes = create_sample_excel_bytes(sheets)
        uploaded_file = SimpleUploadedFile("pricing.xlsx", xlsx_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded_file,
            original_filename="pricing.xlsx",
            file_type=DocumentFileType.EXCEL,
            file_extension="xlsx",
            file_size=len(xlsx_bytes),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            checksum_sha256="xyz789hash",
            uploaded_by=self.user,
        )

        result = DocumentProcessingService.process_quotation_document(doc)

        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.COMPLETED)
        self.assertEqual(doc.processing_progress, 100)

        extraction = doc.extraction_result
        self.assertEqual(extraction.document_type, 'excel')
        self.assertEqual(extraction.pages_or_sheets_count, 1)
        self.assertIn("Gasket Kit", extraction.raw_text)
        self.assertIn("O-Ring Seal", extraction.raw_text)
        self.assertTrue(extraction.has_extractable_text)

    def test_unsupported_format_raises_error(self):
        """Tests that unsupported formats raise UnsupportedDocumentFormatError."""
        with self.assertRaises(UnsupportedDocumentFormatError):
            DocumentProcessingService.get_extractor("docx")


class DocumentProcessingAPITests(APITestCase):
    """API endpoint tests for document extraction."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='api_tester@quoteflow.ai',
            password='Password123!',
        )
        self.org = Organization.objects.create(name='API Org', slug='api-org')
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role=OrganizationRole.ADMIN)

        # Other org for tenant isolation checks
        self.other_org = Organization.objects.create(name='Other Org', slug='other-org')
        self.other_user = User.objects.create_user(
            email='other@quoteflow.ai',
            password='Password123!',
        )
        OrganizationMembership.objects.create(user=self.other_user, organization=self.other_org, role=OrganizationRole.ADMIN)

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-API-001',
            title='API RFQ',
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Beta Industries',
            email='beta@example.com',
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='QT-API-DOC',
            currency='USD',
            created_by=self.user,
        )

        pdf_bytes = create_sample_pdf_bytes(["Sample Invoice\nPart: CNC Flange\nAmount: $500"])
        self.uploaded_file = SimpleUploadedFile("bid.pdf", pdf_bytes, content_type="application/pdf")
        self.doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=self.uploaded_file,
            original_filename="bid.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            checksum_sha256="hash12345",
            uploaded_by=self.user,
        )

    def test_trigger_extraction_endpoint(self):
        """Tests POST /api/quotations/documents/{id}/extract/ triggers text extraction."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/quotations/documents/{self.doc.id}/extract/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['document_type'], 'pdf')
        self.assertIn("CNC Flange", response.data['raw_text'])
        self.assertEqual(response.data['pages_or_sheets_count'], 1)
        self.assertFalse(response.data['is_scanned_or_low_text'])

    def test_get_extraction_result_endpoint(self):
        """Tests GET /api/quotations/documents/{id}/extraction/ retrieves extraction data."""
        self.client.force_authenticate(user=self.user)
        # Pre-process
        DocumentProcessingService.process_quotation_document(self.doc)

        url = f"/api/quotations/documents/{self.doc.id}/extraction/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['document_id']), str(self.doc.id))
        self.assertIn("CNC Flange", response.data['raw_text'])

    def test_tenant_isolation_on_extraction_endpoints(self):
        """Tests that another organization cannot trigger or retrieve extraction results."""
        self.client.force_authenticate(user=self.other_user)
        url = f"/api/quotations/documents/{self.doc.id}/extract/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        url_get = f"/api/quotations/documents/{self.doc.id}/extraction/"
        response_get = self.client.get(url_get)
        self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)


def create_sample_png_bytes(width: int = 400, height: int = 200, color: str = 'white') -> bytes:
    """Helper generating an in-memory PNG image."""
    img = Image.new('RGB', (width, height), color=color)
    stream = io.BytesIO()
    img.save(stream, format='PNG')
    img.close()
    return stream.getvalue()


class OCRExtractorTests(APITestCase):
    """Unit and integration tests for OCR on scanned PDFs and images (PNG, JPG)."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='ocr_tester@quoteflow.ai',
            password='Password123!',
        )
        self.org = Organization.objects.create(name='OCR Org', slug='ocr-org')
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role=OrganizationRole.ADMIN)

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-OCR-001',
            title='OCR RFQ',
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Scanned Supplier Co',
            email='scanned@example.com',
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='QT-OCR-001',
            currency='USD',
            created_by=self.user,
        )

    def test_ocr_engine_availability_check(self):
        """Tests that OCREngine.is_available() safely checks for Tesseract binary without throwing unhandled exceptions."""
        result = OCREngine.is_available()
        self.assertIsInstance(result, bool)

    def test_ocr_engine_graceful_error_when_tesseract_missing(self):
        """Tests that OCREngine raises TesseractNotInstalledError when binary is unavailable."""
        with patch.object(OCREngine, 'is_available', return_value=False):
            with self.assertRaises(TesseractNotInstalledError):
                OCREngine.extract_text(create_sample_png_bytes())

    def test_image_extractor_with_mocked_ocr_success(self):
        """Tests ImageExtractor extracts text and calculates confidence from a PNG image."""
        png_bytes = create_sample_png_bytes()

        mock_text = "INVOICE #INV-2026-PNG\nSupplier: Apex Parts\nTotal: $1,250.00"
        mock_conf = 93.4
        mock_boxes = [
            {'text': 'INVOICE', 'confidence': 95.0, 'bbox': [10, 10, 50, 20]},
            {'text': 'Total:', 'confidence': 91.8, 'bbox': [10, 30, 40, 20]},
        ]

        with patch.object(OCREngine, 'is_available', return_value=True), \
             patch.object(OCREngine, 'extract_text', return_value=(mock_text, mock_conf, mock_boxes)):
            extractor = ImageExtractor()
            result = extractor.extract(png_bytes)

        self.assertEqual(result.document_type, 'image')
        self.assertEqual(result.total_units, 1)
        self.assertEqual(len(result.pages), 1)

        # Check page 1 attributes
        page = result.pages[0]
        self.assertEqual(page.page_number, 1)
        self.assertEqual(page.extraction_method, 'ocr')
        self.assertEqual(page.ocr_confidence, mock_conf)
        self.assertTrue(page.has_text)
        self.assertIn("INVOICE #INV-2026-PNG", page.text)

        # Check overall result metrics
        self.assertTrue(result.was_ocr_performed)
        self.assertEqual(result.ocr_pages, [1])
        self.assertEqual(result.ocr_confidence, mock_conf)
        self.assertTrue(result.has_extractable_text)
        self.assertFalse(result.is_scanned_or_low_text)
        self.assertIn("--- Page 1 of 1 (Scanned Image) ---", result.raw_text)

    def test_image_extractor_when_tesseract_missing_handles_gracefully(self):
        """Tests ImageExtractor handles absent Tesseract gracefully without throwing unhandled exceptions."""
        png_bytes = create_sample_png_bytes()

        with patch.object(OCREngine, 'is_available', return_value=False):
            extractor = ImageExtractor()
            result = extractor.extract(png_bytes)

        self.assertEqual(result.document_type, 'image')
        self.assertFalse(result.has_extractable_text)
        self.assertTrue(result.is_scanned_or_low_text)
        self.assertFalse(result.was_ocr_performed)
        self.assertTrue(any("Tesseract OCR is not installed" in w for w in result.warnings))

    def test_scanned_pdf_automatic_ocr_fallback(self):
        """Tests that a multi-page scanned PDF with 0 native digital text automatically renders pages and runs OCR."""
        # 2 pages with 0 digital text
        pdf_bytes = create_sample_pdf_bytes(["", ""])

        page_1_ocr = "SCANNED BID PAGE 1\nPart: Brass Fitting\nPrice: $18.50"
        page_2_ocr = "SCANNED BID PAGE 2\nPayment: Net 30\nWarranty: 1 Year"

        def mock_ocr_side_effect(img, lang='eng'):
            # Return different OCR text depending on invocation
            mock_ocr_side_effect.calls += 1
            if mock_ocr_side_effect.calls == 1:
                return (page_1_ocr, 90.0, [])
            return (page_2_ocr, 94.0, [])

        mock_ocr_side_effect.calls = 0

        with patch.object(OCREngine, 'is_available', return_value=True), \
             patch.object(OCREngine, 'extract_text', side_effect=mock_ocr_side_effect):
            extractor = PDFExtractor(enable_ocr=True)
            result = extractor.extract(pdf_bytes)

        self.assertEqual(result.document_type, 'pdf')
        self.assertEqual(result.total_units, 2)
        self.assertEqual(len(result.pages), 2)

        # Page 1
        self.assertEqual(result.pages[0].page_number, 1)
        self.assertEqual(result.pages[0].extraction_method, 'ocr')
        self.assertEqual(result.pages[0].ocr_confidence, 90.0)
        self.assertIn("Brass Fitting", result.pages[0].text)

        # Page 2
        self.assertEqual(result.pages[1].page_number, 2)
        self.assertEqual(result.pages[1].extraction_method, 'ocr')
        self.assertEqual(result.pages[1].ocr_confidence, 94.0)
        self.assertIn("Warranty: 1 Year", result.pages[1].text)

        # Overall OCR tracking
        self.assertTrue(result.was_ocr_performed)
        self.assertEqual(result.ocr_pages, [1, 2])
        self.assertEqual(result.ocr_confidence, 92.0)  # average of 90.0 and 94.0
        self.assertTrue(result.has_extractable_text)
        self.assertIn("--- Page 1 of 2 (OCR Extracted) ---", result.raw_text)
        self.assertIn("--- Page 2 of 2 (OCR Extracted) ---", result.raw_text)

    def test_process_image_quotation_document_in_db(self):
        """Tests end-to-end processing of a PNG quotation document in the database, verifying was_ocr_performed and ocr_confidence."""
        png_bytes = create_sample_png_bytes()
        uploaded_file = SimpleUploadedFile("quote_scan.png", png_bytes, content_type="image/png")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded_file,
            original_filename="quote_scan.png",
            file_type=DocumentFileType.IMAGE,
            file_extension="png",
            file_size=len(png_bytes),
            mime_type="image/png",
            checksum_sha256="pnghash123",
            uploaded_by=self.user,
        )

        mock_text = "Apex Machining Co\nQuotation: QT-9988\nTotal: $3,450.00"
        with patch.object(OCREngine, 'is_available', return_value=True), \
             patch.object(OCREngine, 'extract_text', return_value=(mock_text, 95.5, [])):
            result = DocumentProcessingService.process_quotation_document(doc)

        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.COMPLETED)
        self.assertEqual(doc.processing_progress, 100)

        # Verify DB extraction result
        extraction = doc.extraction_result
        self.assertEqual(extraction.document_type, 'image')
        self.assertTrue(extraction.was_ocr_performed)
        self.assertEqual(extraction.ocr_confidence, 95.5)
        self.assertIn("Apex Machining Co", extraction.raw_text)
        self.assertIn("QT-9988", extraction.raw_text)

