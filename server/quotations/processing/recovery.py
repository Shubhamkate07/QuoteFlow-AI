"""
Stale job recovery service for QuoteFlow AI.
Recovers documents and extractions left stranded in PENDING or PROCESSING states
due to Gunicorn timeouts, worker restarts, or server sleeps.
"""

from datetime import timedelta
import logging
from typing import Optional, Dict
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('quoteflow.recovery')

STUCK_INTERRUPTED_MESSAGE = "Processing was interrupted, please retry"


def get_stale_job_timeout_minutes() -> int:
    """Returns configurable stale job timeout in minutes (defaults to 10)."""
    return getattr(settings, 'STALE_JOB_TIMEOUT_MINUTES', 10)


def recover_stuck_documents_and_extractions(
    max_age_minutes: Optional[int] = None,
    document_id: Optional[str] = None,
    organization=None,
) -> Dict[str, int]:
    """
    Marks any documents and extractions in PENDING or PROCESSING states older than
    cutoff as FAILED with a friendly recovery message.
    """
    from quotations.models import QuotationDocument, DocumentProcessingStatus
    from extractions.models import QuotationExtraction, ExtractionStatus

    timeout_min = max_age_minutes if max_age_minutes is not None else get_stale_job_timeout_minutes()
    cutoff = timezone.now() - timedelta(minutes=timeout_min)

    # 1. Recover stuck QuotationDocument records
    doc_qs = QuotationDocument.objects.filter(
        processing_status__in=[DocumentProcessingStatus.PENDING, DocumentProcessingStatus.PROCESSING],
        updated_at__lt=cutoff,
    )
    if document_id:
        doc_qs = doc_qs.filter(id=document_id)
    if organization:
        doc_qs = doc_qs.filter(organization=organization)

    recovered_docs = doc_qs.update(
        processing_status=DocumentProcessingStatus.FAILED,
        processing_error=STUCK_INTERRUPTED_MESSAGE,
        updated_at=timezone.now(),
    )

    # 2. Recover stuck QuotationExtraction records
    ext_qs = QuotationExtraction.objects.filter(
        status__in=[ExtractionStatus.PENDING, ExtractionStatus.PROCESSING],
        updated_at__lt=cutoff,
    )
    if document_id:
        ext_qs = ext_qs.filter(document_id=document_id)
    if organization:
        ext_qs = ext_qs.filter(organization=organization)

    recovered_extractions = ext_qs.update(
        status=ExtractionStatus.FAILED,
        error_message=STUCK_INTERRUPTED_MESSAGE,
        updated_at=timezone.now(),
    )

    if recovered_docs > 0 or recovered_extractions > 0:
        logger.warning(
            "Stale job recovery: marked %d document(s) and %d extraction(s) as FAILED (older than %d minutes)",
            recovered_docs,
            recovered_extractions,
            timeout_min,
        )

    return {
        'recovered_documents': recovered_docs,
        'recovered_extractions': recovered_extractions,
    }
