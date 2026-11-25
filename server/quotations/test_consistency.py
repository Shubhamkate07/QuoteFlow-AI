"""
Tests for Data Consistency, Background Collision, Atomic Approval, and Stale Job Recovery.
Covers:
1. Deletion collision during background processing
2. Atomic approve + apply rollback on failure
3. Rejection of duplicate approval (409 Conflict)
4. Stale-job recovery (marking stuck jobs as FAILED) and management command
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from extractions.models import ExtractionStatus, QuotationExtraction, ReviewStatus
from extractions.services import QuotationExtractionService
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from quotations.models import (
    DocumentFileType,
    DocumentProcessingStatus,
    Quotation,
    QuotationDocument,
    QuotationItem,
)
from quotations.processing.recovery import (
    recover_stuck_documents_and_extractions,
    STUCK_INTERRUPTED_MESSAGE,
)
from quotations.services import delete_quotation, delete_quotation_document
from quotations.tasks import process_document_task
from rfqs.models import RFQ, RFQStatus
from suppliers.models import Supplier
from users.models import User


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ConsistencyAndIntegrityTests(APITestCase):
    """
    Test suite for Prompt 2 consistency, atomic operations, delete collision, and recovery.
    """

    def setUp(self):
        # 1. Tenant organization
        self.org = Organization.objects.create(name="Consistency Test Org", slug="consistency-test-org")

        # 2. Users (Admin and Viewer)
        self.manager_user = User.objects.create_user(
            email="manager@consistency.org",
            password="testpassword123",
            first_name="Procurement",
            last_name="Manager",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.manager_user,
            role=OrganizationRole.PROCUREMENT_MANAGER,
            is_active=True,
        )

        self.viewer_user = User.objects.create_user(
            email="viewer@consistency.org",
            password="testpassword123",
            first_name="Read",
            last_name="Only",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.viewer_user,
            role=OrganizationRole.PROCUREMENT_USER,
            is_active=True,
        )

        # 3. RFQ and Supplier
        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-CONSISTENCY-01",
            title="Consistency RFQ",
            created_by=self.manager_user,
            status=RFQStatus.OPEN,
        )

        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name="Apex Aerospace Parts",
            contact_person="John Apex",
            email="john@apexparts.com",
            created_by=self.manager_user,
        )

        # 4. Quotation and Document
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-CONSISTENCY-01",
            currency="USD",
            created_by=self.manager_user,
        )

        dummy_pdf = SimpleUploadedFile("sample_quote.pdf", b"%PDF-1.4 test dummy content", content_type="application/pdf")
        self.document = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            file=dummy_pdf,
            original_filename="sample_quote.pdf",
            file_type=DocumentFileType.PDF,
            file_extension="pdf",
            file_size=len(dummy_pdf),
            processing_status=DocumentProcessingStatus.PENDING,
            uploaded_by=self.manager_user,
        )

    # -------------------------------------------------------------------------
    # Issue 7 Tests: Delete Collides With Background Processing
    # -------------------------------------------------------------------------

    def test_delete_quotation_during_processing_exits_quietly(self):
        """
        Verifies that if a quotation/document is deleted while background processing
        is dispatched, the task exits cleanly without unhandled DoesNotExist or crash.
        """
        doc_id = str(self.document.id)

        # Delete quotation (cascades to document)
        delete_quotation(quotation=self.quotation)

        # Confirm document was deleted from DB
        self.assertFalse(QuotationDocument.objects.filter(id=doc_id).exists())

        # Execute process_document_task for the deleted document ID
        result = process_document_task(doc_id)

        # Should return an aborted/error dictionary gracefully, not raise an exception
        self.assertIn(result.get('status'), ['aborted', 'error'])

    def test_delete_document_endpoints_return_clear_400_not_500_on_failure(self):
        """
        Verifies that DELETE endpoints catch errors gracefully and return clear HTTP 400.
        """
        self.client.force_authenticate(user=self.manager_user)

        with patch("quotations.services.delete_quotation", side_effect=Exception("Storage backend locked")):
            response = self.client.delete(f"/api/quotations/{self.quotation.id}/")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Failed to delete quotation", response.data['detail'])

        with patch("quotations.services.delete_quotation_document", side_effect=Exception("Permission denied on storage")):
            response = self.client.delete(f"/api/quotations/documents/{self.document.id}/")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Failed to delete document", response.data['detail'])

    # -------------------------------------------------------------------------
    # Issue 11 Tests: Atomic Approve and Apply Transaction
    # -------------------------------------------------------------------------

    def test_atomic_approve_and_apply_rollback_on_failure(self):
        """
        Verifies that when apply_to_quotation fails during approval, both approve
        and apply roll back atomically: the extraction remains UNREVIEWED / not approved,
        and HTTP 400 is returned.
        """
        self.client.force_authenticate(user=self.manager_user)

        self.document.processing_status = DocumentProcessingStatus.COMPLETED
        self.document.save(update_fields=['processing_status'])

        # Create a completed extraction ready for approval
        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            review_status=ReviewStatus.UNREVIEWED,
            is_approved=False,
            extracted_data={
                "line_items": [
                    {
                        "description": "Titanium Bolt M8",
                        "quantity": 100,
                        "unit_price": 5.50,
                    }
                ]
            },
        )

        # Add an initial manual line item to quotation
        manual_item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Manual Pre-existing Item",
            quantity=Decimal('10.00'),
            unit_price=Decimal('25.00'),
            source=QuotationItem.ItemSource.MANUAL,
        )

        # Simulate apply_to_quotation failure
        with patch.object(
            QuotationExtractionService,
            'apply_to_quotation',
            side_effect=Exception("Database connection timed out during apply"),
        ):
            response = self.client.post(
                f"/api/extractions/{extraction.id}/approve/",
                {"review_notes": "All looks good", "apply_to_quotation": True},
                format="json",
            )

            # Must return HTTP 400 with clear error message
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Failed to approve and apply extraction", response.data['detail'])

        # Reload extraction from DB to verify it rolled back to unapproved
        extraction.refresh_from_db()
        self.assertFalse(extraction.is_approved)
        self.assertEqual(extraction.review_status, ReviewStatus.UNREVIEWED)

        # Verify manual item was NOT deleted
        self.assertTrue(QuotationItem.objects.filter(id=manual_item.id).exists())

    def test_approve_double_call_returns_409_conflict(self):
        """
        Verifies that calling approve on an already approved extraction returns 409 Conflict.
        """
        self.client.force_authenticate(user=self.manager_user)

        # Create an already approved extraction
        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            review_status=ReviewStatus.APPROVED,
            is_approved=True,
            approved_by=self.manager_user,
            approved_at=timezone.now(),
        )

        response = self.client.post(
            f"/api/extractions/{extraction.id}/approve/",
            {"review_notes": "Trying to approve again", "apply_to_quotation": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already been approved", response.data['detail'])

    def test_approve_rejects_pending_or_processing_extraction(self):
        """
        Verifies that attempting to approve an extraction while it is still processing returns 400.
        """
        self.client.force_authenticate(user=self.manager_user)

        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.PROCESSING,
            review_status=ReviewStatus.UNREVIEWED,
            is_approved=False,
        )

        response = self.client.post(
            f"/api/extractions/{extraction.id}/approve/",
            {"apply_to_quotation": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("still processing", response.data['detail'])

    # -------------------------------------------------------------------------
    # Issue 12 Tests: Preserve Manual Line Items on Approve
    # -------------------------------------------------------------------------

    def test_approve_preserves_manual_line_items(self):
        """
        Verifies that when an extraction is applied with replace_items=True,
        manual line items are preserved and only extracted items are replaced.
        """
        self.client.force_authenticate(user=self.manager_user)

        self.document.processing_status = DocumentProcessingStatus.COMPLETED
        self.document.save(update_fields=['processing_status'])

        # 1. Existing manual item and existing extraction item
        manual_item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Manual Inspection Fee",
            quantity=Decimal('1'),
            unit_price=Decimal('500.00'),
            source=QuotationItem.ItemSource.MANUAL,
        )
        old_extracted_item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Old Extracted Sensor",
            quantity=Decimal('5'),
            unit_price=Decimal('100.00'),
            source=QuotationItem.ItemSource.EXTRACTION,
        )

        # 2. Completed extraction with new line items
        extraction = QuotationExtraction.objects.create(
            organization=self.org,
            document=self.document,
            quotation=self.quotation,
            status=ExtractionStatus.COMPLETED,
            review_status=ReviewStatus.UNREVIEWED,
            is_approved=False,
            extracted_data={
                "line_items": [
                    {
                        "description": "New Extracted Valve",
                        "quantity": 2,
                        "unit_price": 750.00,
                    }
                ]
            },
        )

        # Approve and apply
        response = self.client.post(
            f"/api/extractions/{extraction.id}/approve/",
            {"apply_to_quotation": True, "replace_items": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manual item must still exist
        self.assertTrue(QuotationItem.objects.filter(id=manual_item.id).exists())

        # Old extracted item must be replaced
        self.assertFalse(QuotationItem.objects.filter(id=old_extracted_item.id).exists())

        # New extracted item must exist with source='extraction'
        new_items = QuotationItem.objects.filter(quotation=self.quotation, source=QuotationItem.ItemSource.EXTRACTION)
        self.assertEqual(new_items.count(), 1)
        self.assertEqual(new_items.first().description, "New Extracted Valve")

    # -------------------------------------------------------------------------
    # Issue 13 Tests: Stale Job Recovery
    # -------------------------------------------------------------------------

    def test_stale_job_recovery_marks_interrupted_tasks_failed(self):
        """
        Verifies that documents and extractions in PENDING/PROCESSING older than
        the threshold are marked FAILED with STUCK_INTERRUPTED_MESSAGE.
        """
        # Create a document stuck in PROCESSING 20 minutes ago
        stuck_doc = QuotationDocument.objects.create(
            organization=self.org,
            quotation=self.quotation,
            original_filename="stuck.pdf",
            file_type=DocumentFileType.PDF,
            file_size=1024,
            processing_status=DocumentProcessingStatus.PROCESSING,
            processing_progress=40,
        )
        # Manually backdate updated_at
        past_time = timezone.now() - timedelta(minutes=25)
        QuotationDocument.objects.filter(id=stuck_doc.id).update(updated_at=past_time)

        # Create an extraction stuck in PROCESSING 20 minutes ago
        stuck_ext = QuotationExtraction.objects.create(
            organization=self.org,
            document=stuck_doc,
            quotation=self.quotation,
            status=ExtractionStatus.PROCESSING,
        )
        QuotationExtraction.objects.filter(id=stuck_ext.id).update(updated_at=past_time)

        # Run recovery
        results = recover_stuck_documents_and_extractions(max_age_minutes=10)
        self.assertGreaterEqual(results['recovered_documents'], 1)
        self.assertGreaterEqual(results['recovered_extractions'], 1)

        stuck_doc.refresh_from_db()
        stuck_ext.refresh_from_db()

        self.assertEqual(stuck_doc.processing_status, DocumentProcessingStatus.FAILED)
        self.assertEqual(stuck_doc.processing_error, STUCK_INTERRUPTED_MESSAGE)

        self.assertEqual(stuck_ext.status, ExtractionStatus.FAILED)
        self.assertEqual(stuck_ext.error_message, STUCK_INTERRUPTED_MESSAGE)

    def test_recover_stuck_jobs_management_command(self):
        """
        Verifies that python manage.py recover_stuck_jobs executes cleanly.
        """
        call_command('recover_stuck_jobs', '--minutes', '15')
