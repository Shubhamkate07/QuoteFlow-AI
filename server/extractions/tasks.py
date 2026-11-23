"""
Asynchronous Celery tasks for AI quotation document extraction in QuoteFlow AI.
Handles background Gemini processing, rate limit retry with exponential backoff,
and document lifecycle updates.
"""

import logging
from celery import shared_task
from django.db import DatabaseError, OperationalError

from ai.exceptions import GeminiAuthenticationError, GeminiConfigurationError, GeminiRateLimitError
from extractions.models import ExtractionStatus, QuotationExtraction
from extractions.services import QuotationExtractionService
from quotations.models import DocumentProcessingStatus, QuotationDocument

logger = logging.getLogger('quoteflow.tasks.extractions')


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="extractions.run_ai_extraction_task",
    track_started=True,
)
def run_ai_extraction_task(self, document_id: str, user_id: str = None) -> dict:
    """
    Background Celery task that executes Gemini AI quotation extraction:
    1. Loads the QuotationDocument.
    2. Runs QuotationExtractionService.extract_from_document.
    3. Handles rate limit and transient retries with exponential backoff.
    4. Updates document processing status and task_id.
    """
    task_id = self.request.id or 'eager-task'
    logger.info("[AIExtractionTask %s] Starting background extraction for Document #%s", task_id, document_id)

    try:
        document = QuotationDocument.objects.select_related('organization', 'quotation').get(id=document_id)
    except QuotationDocument.DoesNotExist:
        logger.error("[AIExtractionTask %s] Document #%s does not exist. Aborting.", task_id, document_id)
        return {'status': 'error', 'message': f'Document #{document_id} not found.'}

    # Record task_id on document
    document.task_id = task_id
    document.processing_status = DocumentProcessingStatus.PROCESSING
    document.processing_progress = 30
    document.save(update_fields=['task_id', 'processing_status', 'processing_progress', 'updated_at'])

    try:
        extraction = QuotationExtractionService.extract_from_document(document)
        extraction.task_id = task_id
        extraction.save(update_fields=['task_id', 'updated_at'])

        if extraction.status == ExtractionStatus.FAILED:
            return {
                'status': 'failed',
                'extraction_id': str(extraction.id),
                'document_id': document_id,
                'error': extraction.error_message,
            }

        return {
            'status': 'completed',
            'extraction_id': str(extraction.id),
            'document_id': document_id,
            'items_count': extraction.items_count,
            'is_math_consistent': extraction.is_math_consistent,
            'currency': extraction.currency,
            'grand_total': str(extraction.stated_grand_total or extraction.calculated_grand_total),
        }

    except GeminiRateLimitError as rate_err:
        countdown = 15 * (2 ** self.request.retries)
        logger.warning(
            "[AIExtractionTask %s] Rate limit hit on Document #%s. Retrying in %ds...",
            task_id, document_id, countdown
        )
        raise self.retry(exc=rate_err, countdown=countdown)

    except (GeminiConfigurationError, GeminiAuthenticationError) as non_retryable:
        error_msg = str(non_retryable)
        logger.error("[AIExtractionTask %s] Non-retryable AI error on Document #%s: %s", task_id, document_id, error_msg)
        document.processing_status = DocumentProcessingStatus.FAILED
        document.processing_error = error_msg
        document.save(update_fields=['processing_status', 'processing_error', 'updated_at'])
        return {'status': 'failed', 'retryable': False, 'error': error_msg}

    except (OperationalError, DatabaseError) as db_err:
        countdown = 10 * (2 ** self.request.retries)
        logger.warning("[AIExtractionTask %s] Database error: %s. Retrying in %ds...", task_id, db_err, countdown)
        raise self.retry(exc=db_err, countdown=countdown)

    except Exception as exc:
        error_msg = f"Extraction failed: {str(exc)}"
        logger.error("[AIExtractionTask %s] Unexpected failure on Document #%s: %s", task_id, document_id, error_msg)
        document.processing_status = DocumentProcessingStatus.FAILED
        document.processing_error = error_msg
        document.save(update_fields=['processing_status', 'processing_error', 'updated_at'])
        return {'status': 'failed', 'retryable': False, 'error': error_msg}
