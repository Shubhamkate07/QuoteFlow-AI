"""
Automated tests for Asynchronous Celery Document Processing in QuoteFlow AI.
Tests background task execution, status tracking, retry handling,
API dispatching, and task status query endpoints.
"""

import io
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
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
from quotations.tasks import process_document_task


def create_sample_pdf(content: str = "Test asynchronous quotation document") -> bytes:
    """Creates a valid PDF byte string for testing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 72), content, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_xlsx() -> bytes:
    """Creates a valid XLSX byte string for testing."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotation"
    ws.append(["Item", "Part Number", "Qty", "Unit Price", "Total"])
    ws.append(["1", "SENS-OPT-01", 100, 45.50, 4550.00])
    stream = io.BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CeleryDocumentTaskTests(APITestCase):
    """
    Tests Celery background task processing with Celery eager mode enabled.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="AeroCorp Task Org", slug="aerocorp-task-org")
        self.user = User.objects.create_user(
            email="tasktester@aerocorp.com",
            password="SecurePassword123!",
            first_name="Task",
            last_name="Tester",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-TASK-001",
            title="Async Sensor RFQ",
            status=RFQStatus.OPEN,
            created_by=self.user,
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Apex Dynamics Async Ltd",
            contact_person="Alex Rivera",
            email="alex@apexdynamics.com",
            country="United States",
        )
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-TASK-001",
            currency="USD",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

        # Mock out asynchronous AI extraction dispatch so document tasks don't make live Gemini API calls
        self.mock_ai_delay_patcher = patch('extractions.tasks.run_ai_extraction_task.delay')
        self.mock_ai_delay = self.mock_ai_delay_patcher.start()
        self.addCleanup(self.mock_ai_delay_patcher.stop)

    def test_process_document_task_pdf_success(self):
        """
        Verifies that process_document_task extracts a PDF, creates DocumentExtractionResult,
        and marks document processing_status as COMPLETED with 100% progress.
        """
        pdf_bytes = create_sample_pdf("Asynchronous Celery Text: Part #ABC-999, Price $500")
        uploaded = SimpleUploadedFile("quote_async.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="quote_async.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        # Execute task directly
        result = process_document_task(str(doc.id))

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['document_id'], str(doc.id))
        self.assertEqual(result['document_type'], 'pdf')
        self.assertGreater(result['word_count'], 0)

        # Verify database updates
        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.COMPLETED)
        self.assertEqual(doc.processing_progress, 100)
        self.assertEqual(doc.processing_error, "")

        # Verify extraction result record
        extraction = DocumentExtractionResult.objects.get(document=doc)
        self.assertIn("ABC-999", extraction.raw_text)
        self.assertTrue(extraction.has_extractable_text)
        self.assertFalse(extraction.is_scanned_or_low_text)

    def test_process_document_task_excel_success(self):
        """
        Verifies that process_document_task extracts an Excel workbook asynchronously.
        """
        xlsx_bytes = create_sample_xlsx()
        uploaded = SimpleUploadedFile("quote_table.xlsx", xlsx_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="quote_table.xlsx",
            file_type=DocumentFileType.EXCEL,
            file_extension=".xlsx",
            file_size=len(xlsx_bytes),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            uploaded_by=self.user,
        )

        result = process_document_task(str(doc.id))

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['document_type'], 'excel')

        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.COMPLETED)
        self.assertEqual(doc.processing_progress, 100)

        extraction = DocumentExtractionResult.objects.get(document=doc)
        self.assertIn("SENS-OPT-01", extraction.raw_text)

    def test_process_document_task_nonexistent_id(self):
        """
        Verifies that calling process_document_task with an invalid/missing ID fails safely with an error dictionary.
        """
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = process_document_task(fake_id)

        self.assertEqual(result['status'], 'error')
        self.assertIn("does not exist", result['message'])

    def test_process_document_task_corrupt_file_fails_without_retry(self):
        """
        Verifies that a corrupt document triggers non-retryable failure handling,
        setting processing_status to FAILED and populating processing_error.
        """
        corrupt_bytes = b"%PDF-1.4 completely corrupt non-decodable garbage content"
        uploaded = SimpleUploadedFile("corrupt.pdf", corrupt_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="corrupt.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(corrupt_bytes),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        result = process_document_task(str(doc.id))

        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['retryable'], False)

        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, DocumentProcessingStatus.FAILED)
        self.assertTrue(
            "failed to open" in doc.processing_error.lower() or
            "corrupt" in doc.processing_error.lower()
        )

    def test_upload_endpoint_triggers_celery_task(self):
        """
        Tests POST /api/quotations/upload/ triggers async Celery task
        and returns immediately with 201 Created.
        """
        pdf_bytes = create_sample_pdf("Commercial Proposal for Turbine Blades")
        uploaded = SimpleUploadedFile("turbine_quote.pdf", pdf_bytes, content_type="application/pdf")

        response = self.client.post(
            "/api/quotations/upload/",
            {
                "rfq_id": str(self.rfq.id),
                "supplier_id": str(self.supplier.id),
                "quotation_number": "QT-ASYNC-TURB-01",
                "file": uploaded,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_data = response.data['documents'][0]
        self.assertTrue(doc_data['task_id'])
        self.assertEqual(doc_data['processing_status'], 'completed')

    def test_document_create_triggers_celery_task(self):
        """
        Tests POST /api/quotations/<id>/documents/ triggers async processing.
        """
        pdf_bytes = create_sample_pdf("Addendum attachment document")
        uploaded = SimpleUploadedFile("addendum.pdf", pdf_bytes, content_type="application/pdf")

        response = self.client.post(
            f"/api/quotations/{self.quotation.id}/documents/",
            {"file": uploaded},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['task_id'])

    def test_extract_endpoint_async_dispatch(self):
        """
        Tests POST /api/quotations/documents/<id>/extract/ defaults to async mode (HTTP 202 ACCEPTED)
        and returns task_id and task_status_url.
        """
        pdf_bytes = create_sample_pdf("Manual re-extract trigger test")
        uploaded = SimpleUploadedFile("re_extract.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="re_extract.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        # POST /api/quotations/documents/<id>/extract/?async=true
        response = self.client.post(f"/api/quotations/documents/{doc.id}/extract/?async=true")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertTrue(response.data['task_id'])
        self.assertIn("task-status", response.data['task_status_url'])

    def test_extract_endpoint_sync_param(self):
        """
        Tests POST /api/quotations/documents/<id>/extract/?sync=true executes synchronously (HTTP 200 OK).
        """
        pdf_bytes = create_sample_pdf("Synchronous extraction test line")
        uploaded = SimpleUploadedFile("sync_extract.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="sync_extract.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        response = self.client.post(f"/api/quotations/documents/{doc.id}/extract/?sync=true")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['document_id'], str(doc.id))
        self.assertIn("Synchronous extraction test line", response.data['raw_text'])

    def test_task_status_endpoint(self):
        """
        Tests GET /api/quotations/documents/<id>/task-status/ returns progress and state.
        """
        pdf_bytes = create_sample_pdf("Status verification document")
        uploaded = SimpleUploadedFile("status_check.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="status_check.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            task_id="mock-celery-task-999",
            processing_status=DocumentProcessingStatus.PROCESSING,
            processing_progress=50,
            uploaded_by=self.user,
        )

        response = self.client.get(f"/api/quotations/documents/{doc.id}/task-status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['document_id'], str(doc.id))
        self.assertEqual(response.data['task_id'], "mock-celery-task-999")
        self.assertEqual(response.data['processing_status'], 'processing')
        self.assertEqual(response.data['processing_progress'], 50)
        self.assertFalse(response.data['has_extraction_result'])

    def test_task_status_organization_isolation(self):
        """
        Verifies that a user from another organization cannot view another organization's document task status.
        """
        other_org = Organization.objects.create(name="Competitor Org", slug="competitor-org")
        other_user = User.objects.create_user(
            email="spy@competitor.com",
            password="CompetitorPassword123!",
            first_name="Rival",
            last_name="User",
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=other_user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
        )

        pdf_bytes = create_sample_pdf("Confidential specs")
        uploaded = SimpleUploadedFile("confidential.pdf", pdf_bytes, content_type="application/pdf")

        doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=uploaded,
            original_filename="confidential.pdf",
            file_type=DocumentFileType.PDF,
            file_extension=".pdf",
            file_size=len(pdf_bytes),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )

        # Authenticate as other user
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/quotations/documents/{doc.id}/task-status/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
