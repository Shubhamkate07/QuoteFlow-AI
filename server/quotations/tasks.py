"""
Celery asynchronous tasks for Quotation Document Processing in QuoteFlow AI.
Handles background text extraction (PDF, Excel, OCR), status updates,
retry strategies with exponential backoff, and robust error tracking.
"""

import logging
from celery import shared_task
from django.db import DatabaseError, OperationalError
from django.utils import timezone

from quotations.models import QuotationDocument, DocumentProcessingStatus
from quotations.processing import (
    DocumentProcessingService,
    CorruptDocumentError,
    DocumentProcessingError,
    EmptyDocumentError,
    UnsupportedDocumentFormatError,
)

logger = logging.getLogger('quoteflow.tasks.documents')


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="quotations.process_document_task",
    track_started=True,
)
def process_document_task(self, document_id: str) -> dict:
    """
    Asynchronous Celery task that processes an uploaded quotation document:
    1. Loads the document from PostgreSQL.
    2. Updates status to 'processing' with incremental progress.
    3. Runs text extraction (PyMuPDF for PDF, openpyxl for Excel, Tesseract for OCR).
    4. Persists the extraction result into DocumentExtractionResult.
    5. Updates document status to 'completed' with 100% progress.
    6. Retries transient database/IO errors with exponential backoff.
    7. Fails gracefully without retrying on corrupt or unsupported formats.
    """
    task_id = self.request.id or 'eager-task'
    attempt = self.request.retries + 1
    max_attempts = self.max_retries + 1

    logger.info(
        "[DocumentTask %s] Starting background processing for Document ID: %s (attempt %d/%d)",
        task_id,
        document_id,
        attempt,
        max_attempts,
    )

    try:
        document = QuotationDocument.objects.select_related('organization', 'quotation').get(id=document_id)
    except QuotationDocument.DoesNotExist:
        logger.info(
            "[DocumentTask %s] QuotationDocument #%s not found in database or already deleted. Exiting quietly.",
            task_id,
            document_id,
        )
        return {
            'status': 'error',
            'document_id': document_id,
            'task_id': task_id,
            'message': f'QuotationDocument #{document_id} does not exist.',
        }

    # Ensure document has task_id stored
    if not document.task_id or document.task_id != task_id:
        if not QuotationDocument.objects.filter(id=document_id).exists():
            return {'status': 'aborted', 'document_id': document_id, 'task_id': task_id}
        QuotationDocument.objects.filter(id=document_id).update(task_id=task_id, updated_at=timezone.now())

    try:
        # Run extraction pipeline
        result = DocumentProcessingService.process_quotation_document(document, save=True)

        if not QuotationDocument.objects.filter(id=document_id).exists():
            logger.info("[DocumentTask %s] Document #%s deleted during processing. Exiting quietly.", task_id, document_id)
            return {'status': 'aborted', 'document_id': document_id, 'task_id': task_id}

        logger.info(
            "[DocumentTask %s] Document #%s successfully processed: type=%s, units=%d, words=%d, ocr=%s, time=%.2fms",
            task_id,
            document_id,
            result.document_type,
            result.total_units,
            result.word_count,
            result.was_ocr_performed,
            result.processing_time_ms,
        )

        # Automatically trigger Gemini AI extraction on the processed document asynchronously
        try:
            from extractions.tasks import run_ai_extraction_task

            doc_id_for_ai = str(document.id)
            run_ai_extraction_task.apply(args=[doc_id_for_ai])
            logger.info("[DocumentTask %s] Dispatched run_ai_extraction_task for Document #%s", task_id, document_id)
        except Exception as ai_dispatch_err:
            logger.warning(
                "[DocumentTask %s] Could not automatically trigger AI extraction for Document #%s: %s",
                task_id,
                document_id,
                ai_dispatch_err,
            )

        return {
            'status': 'completed',
            'document_id': str(document.id),
            'task_id': task_id,
            'document_type': result.document_type,
            'pages_or_sheets_count': result.total_units,
            'character_count': result.character_count,
            'word_count': result.word_count,
            'was_ocr_performed': result.was_ocr_performed,
            'ocr_confidence': result.ocr_confidence,
            'processing_time_ms': result.processing_time_ms,
        }

    except (CorruptDocumentError, UnsupportedDocumentFormatError, EmptyDocumentError, FileNotFoundError) as non_retryable:
        # Permanent format errors: do not retry
        error_msg = str(non_retryable)
        logger.error(
            "[DocumentTask %s] Non-retryable extraction failure on Document #%s: %s",
            task_id,
            document_id,
            error_msg,
        )
        if QuotationDocument.objects.filter(id=document_id).exists():
            QuotationDocument.objects.filter(id=document_id).update(
                processing_status=DocumentProcessingStatus.FAILED,
                processing_progress=0,
                processing_error=error_msg,
                updated_at=timezone.now(),
            )

        return {
            'status': 'failed',
            'document_id': str(document.id),
            'task_id': task_id,
            'error': error_msg,
            'retryable': False,
        }

    except (OperationalError, DatabaseError, IOError) as transient_err:
        # Transient errors: retry with exponential backoff (10s, 20s, 40s)
        countdown = 10 * (2 ** self.request.retries)
        if self.request.retries < self.max_retries:
            logger.warning(
                "[DocumentTask %s] Transient error on Document #%s: %s. Retrying in %ds (attempt %d/%d)...",
                task_id,
                document_id,
                transient_err,
                countdown,
                attempt,
                max_attempts,
            )
            raise self.retry(exc=transient_err, countdown=countdown)
        else:
            error_msg = f"Processing failed after {max_attempts} attempts: {str(transient_err)}"
            logger.error(
                "[DocumentTask %s] Retries exhausted for Document #%s: %s",
                task_id,
                document_id,
                error_msg,
            )
            if QuotationDocument.objects.filter(id=document_id).exists():
                QuotationDocument.objects.filter(id=document_id).update(
                    processing_status=DocumentProcessingStatus.FAILED,
                    processing_progress=0,
                    processing_error=error_msg,
                    updated_at=timezone.now(),
                )
            raise

    except Exception as exc:
        # Generic unhandled failure
        error_msg = f"Unexpected processing error: {str(exc)}"
        logger.exception(
            "[DocumentTask %s] Unexpected exception processing Document #%s: %s",
            task_id,
            document_id,
            error_msg,
        )
        if QuotationDocument.objects.filter(id=document_id).exists():
            QuotationDocument.objects.filter(id=document_id).update(
                processing_status=DocumentProcessingStatus.FAILED,
                processing_progress=0,
                processing_error=error_msg,
                updated_at=timezone.now(),
            )
        raise
