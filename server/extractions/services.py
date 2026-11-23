"""
Services for AI Quotation Extraction, Human Review Workflows, and Commercial Synchronization in QuoteFlow AI.
Orchestrates text retrieval, Gemini prompt synthesis, structured Pydantic decoding,
deterministic arithmetic verification, human review corrections, audit history tracking,
and quotation line-item application.
"""

import copy
from decimal import Decimal
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from ai.service import GeminiService
from extractions.models import (
    CorrectionType,
    ExtractionStatus,
    QuotationExtraction,
    QuotationExtractionCorrection,
    ReviewStatus,
)
from extractions.prompts import EXTRACTION_SYSTEM_INSTRUCTION, build_quotation_extraction_prompt
from extractions.schemas import QuotationExtractionSchema
from extractions.verification import QuotationVerificationEngine, _to_decimal
from quotations.models import (
    DocumentProcessingStatus,
    Quotation,
    QuotationDocument,
    QuotationItem,
)
from quotations.processing import DocumentProcessingService

logger = logging.getLogger('quoteflow.extractions.service')


class QuotationExtractionService:
    """
    Core orchestrator for AI-powered quotation document extraction.
    """

    @classmethod
    def extract_from_document(
        cls,
        document: QuotationDocument,
        user=None,
        model_name: Optional[str] = None,
    ) -> QuotationExtraction:
        """
        Extracts structured quotation data from an uploaded QuotationDocument:
        1. Ensures raw text / OCR results exist for the document.
        2. Prepares page-tagged extraction prompt.
        3. Calls Gemini API using strongly typed QuotationExtractionSchema.
        4. Performs independent arithmetic and logical verification.
        5. Persists the QuotationExtraction record with an immutable initial snapshot.
        """
        org = document.organization
        logger.info(
            "Starting AI quotation extraction for Document #%s (%s, Org #%s)",
            document.id,
            document.original_filename,
            org.id,
        )

        # 1. Ensure document has extraction result (run PyMuPDF/OCR pipeline if not yet processed)
        extraction_model = getattr(document, 'extraction_result', None)
        if not extraction_model or not extraction_model.raw_text.strip():
            logger.info("Document #%s has no text extraction result; running document processor...", document.id)
            DocumentProcessingService.process_quotation_document(document, save=True)
            extraction_model = document.extraction_result

        raw_text = extraction_model.raw_text or ""
        structured_content = extraction_model.structured_content or {}

        if not raw_text.strip():
            logger.warning("Document #%s contains zero extractable text.", document.id)
            extraction_record = QuotationExtraction.objects.create(
                organization=org,
                document=document,
                quotation=document.quotation,
                status=ExtractionStatus.FAILED,
                error_message="Document contains zero extractable digital text or OCR content.",
            )
            return extraction_record

        # 2. Build multi-page prompt
        prompt = build_quotation_extraction_prompt(
            raw_text=raw_text,
            structured_content=structured_content,
            document_type=document.file_type,
            filename=document.original_filename,
        )

        # 3. Create initial QuotationExtraction record
        ai_service = GeminiService()
        active_model = model_name or ai_service.config.model_name

        extraction_record = QuotationExtraction.objects.create(
            organization=org,
            document=document,
            quotation=document.quotation,
            status=ExtractionStatus.PROCESSING,
            model_name=active_model,
        )

        # 4. Invoke Gemini with structured JSON schema
        start_time = time.time()
        try:
            parsed_data: QuotationExtractionSchema = ai_service.generate_structured(
                prompt=prompt,
                response_schema=QuotationExtractionSchema,
                system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                temperature=0.0,  # Zero temperature for maximum determinism
                model=active_model,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
        except Exception as ai_err:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error("Gemini AI extraction failed for Document #%s: %s", document.id, ai_err)
            extraction_record.status = ExtractionStatus.FAILED
            extraction_record.error_message = str(ai_err)
            extraction_record.processing_time_ms = elapsed_ms
            extraction_record.save(update_fields=['status', 'error_message', 'processing_time_ms', 'updated_at'])
            return extraction_record

        # 5. Independent Arithmetic and Logical Verification
        audit = QuotationVerificationEngine.verify(parsed_data)

        # 6. Populate extraction record fields
        extraction_record.status = ExtractionStatus.COMPLETED
        extraction_record.processing_time_ms = elapsed_ms
        extraction_record.extracted_data = parsed_data.model_dump()
        # Preserve pristine snapshot of AI extraction before human review
        extraction_record.original_extracted_data = copy.deepcopy(extraction_record.extracted_data)
        extraction_record.overall_confidence = parsed_data.overall_confidence

        # Review lifecycle initial state
        extraction_record.review_status = ReviewStatus.UNREVIEWED
        extraction_record.is_approved = False

        # Supplier info
        extraction_record.supplier_name = (parsed_data.supplier.supplier_name or '').strip()
        extraction_record.quotation_number = (parsed_data.supplier.quotation_number or '').strip()
        extraction_record.contact_person = (parsed_data.supplier.contact_person or '').strip()
        extraction_record.contact_email = (parsed_data.supplier.email or '').strip()
        extraction_record.contact_phone = (parsed_data.supplier.phone or '').strip()
        extraction_record.supplier_address = (parsed_data.supplier.address or '').strip()

        # Quotation metadata
        extraction_record.quotation_date = audit.parsed_quotation_date
        extraction_record.validity_date = audit.parsed_validity_date
        extraction_record.currency = audit.normalized_currency

        # Commercial terms
        terms = parsed_data.commercial_terms
        extraction_record.delivery_time = (terms.delivery_time or '').strip()
        extraction_record.delivery_terms = (terms.delivery_terms or '').strip()
        extraction_record.payment_terms = (terms.payment_terms or '').strip()
        extraction_record.warranty = (terms.warranty or '').strip()
        extraction_record.notes = (terms.notes or '').strip()

        # Stated totals
        q_totals = parsed_data.quotation
        extraction_record.stated_subtotal = _to_decimal(q_totals.subtotal)
        extraction_record.stated_tax = _to_decimal(q_totals.tax)
        extraction_record.stated_discount = _to_decimal(q_totals.discount)
        extraction_record.stated_shipping = _to_decimal(q_totals.shipping)
        extraction_record.stated_grand_total = _to_decimal(q_totals.grand_total)

        # Verification metrics
        extraction_record.calculated_items_subtotal = audit.calculated_items_subtotal
        extraction_record.calculated_grand_total = audit.calculated_grand_total
        extraction_record.total_variance = audit.total_variance
        extraction_record.is_math_consistent = audit.is_math_consistent
        extraction_record.validation_warnings = audit.validation_flags
        extraction_record.items_count = audit.items_count

        extraction_record.save()

        # Update document progress
        document.processing_status = DocumentProcessingStatus.COMPLETED
        document.processing_progress = 100
        document.processing_error = ""
        document.save(update_fields=['processing_status', 'processing_progress', 'processing_error', 'updated_at'])

        logger.info(
            "AI extraction completed for Document #%s: %d items, total=%s %s, consistent=%s, warnings=%d",
            document.id,
            extraction_record.items_count,
            extraction_record.currency,
            extraction_record.stated_grand_total or extraction_record.calculated_grand_total,
            extraction_record.is_math_consistent,
            len(extraction_record.validation_warnings),
        )
        return extraction_record

    @classmethod
    @transaction.atomic
    def apply_to_quotation(
        cls,
        extraction: QuotationExtraction,
        user=None,
        replace_items: bool = True,
    ) -> Quotation:
        """
        Synchronizes verified AI extraction data into the official Quotation and QuotationItem records.
        Applies any human-corrected values rather than raw unreviewed AI data.
        """
        quotation = extraction.quotation
        if not quotation:
            raise ValidationError("Extraction record is not attached to a Quotation.")

        # Cross-tenant security check
        if quotation.organization_id != extraction.organization_id:
            raise ValidationError("Security violation: Extraction and quotation organizations do not match.")

        # 1. Update quotation commercial attributes if provided
        if extraction.quotation_date and not quotation.quotation_date:
            quotation.quotation_date = extraction.quotation_date

        if extraction.validity_date and not quotation.validity_date:
            quotation.validity_date = extraction.validity_date

        if extraction.currency:
            quotation.currency = extraction.currency

        if extraction.delivery_terms and not quotation.delivery_terms:
            quotation.delivery_terms = extraction.delivery_terms

        if extraction.payment_terms and not quotation.payment_terms:
            quotation.payment_terms = extraction.payment_terms

        if extraction.warranty and not quotation.warranty_information:
            quotation.warranty_information = extraction.warranty

        if extraction.notes and not quotation.notes:
            quotation.notes = extraction.notes

        # 2. Synchronize Line Items (uses current working data, reflecting human edits)
        raw_items = extraction.extracted_data.get('line_items', [])
        if replace_items and raw_items:
            quotation.items.all().delete()

        for idx, item_data in enumerate(raw_items, start=1):
            desc = (item_data.get('description') or f"Line Item #{idx}").strip()
            qty = Decimal(str(item_data.get('quantity') or 1.0))
            price = Decimal(str(item_data.get('unit_price') or 0.0))
            discount = Decimal(str(item_data.get('discount') or 0.0))
            tax = Decimal(str(item_data.get('tax') or 0.0))
            unit = (item_data.get('unit') or 'PCS')[:50]
            manufacturer = (item_data.get('manufacturer') or '')[:255]
            model_number = (item_data.get('model') or '')[:100]

            # Convert specs list of dicts to a flat dict
            raw_specs = item_data.get('specifications', [])
            specs_dict = {}
            if isinstance(raw_specs, list):
                for s in raw_specs:
                    if isinstance(s, dict) and 'name' in s and 'value' in s:
                        specs_dict[str(s['name'])] = str(s['value'])

            QuotationItem.objects.create(
                quotation=quotation,
                position=item_data.get('line_number') or idx,
                description=desc,
                manufacturer=manufacturer,
                model=model_number,
                quantity=max(Decimal('0.0001'), qty),
                unit=unit,
                unit_price=max(Decimal('0.0000'), price),
                discount=max(Decimal('0.00'), discount),
                tax=max(Decimal('0.00'), tax),
                specifications=specs_dict,
                notes=item_data.get('source_text') or '',
            )

        # 3. Recalculate quotation subtotal and grand totals from line items
        quotation.recalculate_totals(save=False)
        quotation.save()

        # 4. Mark extraction as applied
        extraction.is_applied_to_quotation = True
        extraction.applied_at = timezone.now()
        extraction.applied_by = user
        extraction.save(update_fields=['is_applied_to_quotation', 'applied_at', 'applied_by', 'updated_at'])

        logger.info("Successfully applied AI extraction #%s to Quotation #%s", extraction.id, quotation.id)
        return quotation


class QuotationReviewService:
    """
    Manages human review workflows, field corrections, audit logging,
    and formal approvals for AI-extracted quotation documents.
    """

    @classmethod
    @transaction.atomic
    def apply_corrections(
        cls,
        extraction: QuotationExtraction,
        updates: Dict[str, Any],
        user,
        reason: str = "",
        mark_reviewed: bool = True,
    ) -> Tuple[QuotationExtraction, List[QuotationExtractionCorrection]]:
        """
        Applies human corrections to supplier, quotation header, line items, and commercial terms.
        Records an audit history log in QuotationExtractionCorrection for every modified field.
        Re-executes the deterministic validation engine to recompute arithmetic totals and flags.
        """
        # Ensure original AI extraction is preserved before first modification
        if not extraction.original_extracted_data:
            extraction.original_extracted_data = copy.deepcopy(extraction.extracted_data)

        current_data = copy.deepcopy(extraction.extracted_data)
        created_corrections = []
        reviewed_fields = set(extraction.reviewed_fields or [])

        # 1. Supplier Information Corrections
        if 'supplier' in updates and isinstance(updates['supplier'], dict):
            supplier_updates = updates['supplier']
            curr_supplier = current_data.setdefault('supplier', {})
            for key, new_val in supplier_updates.items():
                old_val = curr_supplier.get(key)
                if old_val != new_val:
                    corr = QuotationExtractionCorrection.objects.create(
                        organization=extraction.organization,
                        extraction=extraction,
                        correction_type=CorrectionType.SUPPLIER,
                        field_path=f"supplier.{key}",
                        previous_value=old_val,
                        new_value=new_val,
                        reason=reason,
                        corrected_by=user,
                    )
                    created_corrections.append(corr)
                    curr_supplier[key] = new_val
                    if mark_reviewed:
                        reviewed_fields.add(f"supplier.{key}")

        # 2. Quotation Header / Financial Totals Corrections
        if 'quotation' in updates and isinstance(updates['quotation'], dict):
            quote_updates = updates['quotation']
            curr_quote = current_data.setdefault('quotation', {})
            for key, new_val in quote_updates.items():
                old_val = curr_quote.get(key)
                if old_val != new_val:
                    corr_type = (
                        CorrectionType.TAX_SHIPPING
                        if key in {'tax', 'shipping'}
                        else CorrectionType.QUOTATION_HEADER
                    )
                    corr = QuotationExtractionCorrection.objects.create(
                        organization=extraction.organization,
                        extraction=extraction,
                        correction_type=corr_type,
                        field_path=f"quotation.{key}",
                        previous_value=old_val,
                        new_value=new_val,
                        reason=reason,
                        corrected_by=user,
                    )
                    created_corrections.append(corr)
                    curr_quote[key] = new_val
                    if mark_reviewed:
                        reviewed_fields.add(f"quotation.{key}")

        # 3. Commercial Terms Corrections
        if 'commercial_terms' in updates and isinstance(updates['commercial_terms'], dict):
            terms_updates = updates['commercial_terms']
            curr_terms = current_data.setdefault('commercial_terms', {})
            for key, new_val in terms_updates.items():
                old_val = curr_terms.get(key)
                if old_val != new_val:
                    corr = QuotationExtractionCorrection.objects.create(
                        organization=extraction.organization,
                        extraction=extraction,
                        correction_type=CorrectionType.COMMERCIAL_TERMS,
                        field_path=f"commercial_terms.{key}",
                        previous_value=old_val,
                        new_value=new_val,
                        reason=reason,
                        corrected_by=user,
                    )
                    created_corrections.append(corr)
                    curr_terms[key] = new_val
                    if mark_reviewed:
                        reviewed_fields.add(f"commercial_terms.{key}")

        # 4. Line Items Corrections (Price, Quantity, Specifications, Description, Unit)
        if 'line_items' in updates and isinstance(updates['line_items'], list):
            new_line_items = updates['line_items']
            old_line_items = current_data.get('line_items', [])

            for idx, new_item in enumerate(new_line_items):
                field_base = f"line_items[{idx}]"
                if idx < len(old_line_items):
                    old_item = old_line_items[idx]
                    # Check price
                    if old_item.get('unit_price') != new_item.get('unit_price'):
                        created_corrections.append(QuotationExtractionCorrection.objects.create(
                            organization=extraction.organization,
                            extraction=extraction,
                            correction_type=CorrectionType.PRICE,
                            field_path=f"{field_base}.unit_price",
                            previous_value=old_item.get('unit_price'),
                            new_value=new_item.get('unit_price'),
                            reason=reason,
                            corrected_by=user,
                        ))
                    # Check quantity
                    if old_item.get('quantity') != new_item.get('quantity'):
                        created_corrections.append(QuotationExtractionCorrection.objects.create(
                            organization=extraction.organization,
                            extraction=extraction,
                            correction_type=CorrectionType.QUANTITY,
                            field_path=f"{field_base}.quantity",
                            previous_value=old_item.get('quantity'),
                            new_value=new_item.get('quantity'),
                            reason=reason,
                            corrected_by=user,
                        ))
                    # Check specifications
                    if old_item.get('specifications') != new_item.get('specifications'):
                        created_corrections.append(QuotationExtractionCorrection.objects.create(
                            organization=extraction.organization,
                            extraction=extraction,
                            correction_type=CorrectionType.SPECIFICATION,
                            field_path=f"{field_base}.specifications",
                            previous_value=old_item.get('specifications'),
                            new_value=new_item.get('specifications'),
                            reason=reason,
                            corrected_by=user,
                        ))
                    # Check general fields
                    for k in ('description', 'model', 'unit', 'discount', 'tax', 'total'):
                        if k in new_item and old_item.get(k) != new_item.get(k):
                            created_corrections.append(QuotationExtractionCorrection.objects.create(
                                organization=extraction.organization,
                                extraction=extraction,
                                correction_type=CorrectionType.LINE_ITEM,
                                field_path=f"{field_base}.{k}",
                                previous_value=old_item.get(k),
                                new_value=new_item.get(k),
                                reason=reason,
                                corrected_by=user,
                            ))
                else:
                    # Brand new line item added
                    created_corrections.append(QuotationExtractionCorrection.objects.create(
                        organization=extraction.organization,
                        extraction=extraction,
                        correction_type=CorrectionType.LINE_ITEM,
                        field_path=field_base,
                        previous_value=None,
                        new_value=new_item,
                        reason=reason,
                        corrected_by=user,
                    ))
                if mark_reviewed:
                    reviewed_fields.add(field_base)

            current_data['line_items'] = new_line_items

        # 5. Re-run Pure Python Deterministic Validation on Updated Data
        extraction.extracted_data = current_data
        audit = QuotationVerificationEngine.verify(QuotationExtractionSchema.model_validate(current_data))

        # 6. Synchronize Staged Model Fields
        extraction.is_math_consistent = audit.is_math_consistent
        extraction.validation_warnings = audit.validation_flags
        extraction.calculated_items_subtotal = audit.calculated_items_subtotal
        extraction.calculated_grand_total = audit.calculated_grand_total
        extraction.total_variance = audit.total_variance
        extraction.items_count = audit.items_count
        extraction.quotation_date = audit.parsed_quotation_date
        extraction.validity_date = audit.parsed_validity_date
        extraction.currency = audit.normalized_currency

        # Update high-level summary fields
        supp = current_data.get('supplier', {})
        extraction.supplier_name = (supp.get('supplier_name') or '').strip()
        extraction.quotation_number = (supp.get('quotation_number') or '').strip()
        extraction.contact_person = (supp.get('contact_person') or '').strip()
        extraction.contact_email = (supp.get('email') or '').strip()
        extraction.contact_phone = (supp.get('phone') or '').strip()
        extraction.supplier_address = (supp.get('address') or '').strip()

        q_dict = current_data.get('quotation', {})
        extraction.stated_subtotal = _to_decimal(q_dict.get('subtotal'))
        extraction.stated_tax = _to_decimal(q_dict.get('tax'))
        extraction.stated_discount = _to_decimal(q_dict.get('discount'))
        extraction.stated_shipping = _to_decimal(q_dict.get('shipping'))
        extraction.stated_grand_total = _to_decimal(q_dict.get('grand_total'))

        terms = current_data.get('commercial_terms', {})
        extraction.delivery_time = (terms.get('delivery_time') or '').strip()
        extraction.delivery_terms = (terms.get('delivery_terms') or '').strip()
        extraction.payment_terms = (terms.get('payment_terms') or '').strip()
        extraction.warranty = (terms.get('warranty') or '').strip()
        extraction.notes = (terms.get('notes') or '').strip()

        # 7. Update Human Review Status & Audit Metrics
        if created_corrections:
            extraction.has_human_corrections = True
            extraction.corrections_count = extraction.corrections.count()

        extraction.reviewed_fields = sorted(list(reviewed_fields))
        extraction.reviewed_by = user
        extraction.reviewed_at = timezone.now()

        if extraction.review_status == ReviewStatus.UNREVIEWED:
            extraction.review_status = ReviewStatus.IN_REVIEW

        extraction.save()
        logger.info(
            "Applied %d corrections to Extraction #%s by user %s (consistent: %s)",
            len(created_corrections),
            extraction.id,
            getattr(user, 'email', str(user)),
            extraction.is_math_consistent,
        )
        return extraction, created_corrections

    @classmethod
    def mark_fields_reviewed(cls, extraction: QuotationExtraction, fields: List[str], user) -> QuotationExtraction:
        """Marks specific field paths as verified by a human reviewer."""
        current = set(extraction.reviewed_fields or [])
        current.update(fields)
        extraction.reviewed_fields = sorted(list(current))
        extraction.reviewed_by = user
        extraction.reviewed_at = timezone.now()
        if extraction.review_status == ReviewStatus.UNREVIEWED:
            extraction.review_status = ReviewStatus.IN_REVIEW
        extraction.save(update_fields=['reviewed_fields', 'reviewed_by', 'reviewed_at', 'review_status', 'updated_at'])
        return extraction

    @classmethod
    def approve_extraction(
        cls,
        extraction: QuotationExtraction,
        user,
        review_notes: str = "",
    ) -> QuotationExtraction:
        """Approves the extraction for procurement execution."""
        extraction.is_approved = True
        extraction.review_status = ReviewStatus.APPROVED
        extraction.approved_by = user
        extraction.approved_at = timezone.now()
        if review_notes:
            extraction.review_notes = review_notes
        extraction.save(update_fields=['is_approved', 'review_status', 'approved_by', 'approved_at', 'review_notes', 'updated_at'])
        logger.info("Extraction #%s approved by %s", extraction.id, getattr(user, 'email', str(user)))
        return extraction

    @classmethod
    def reject_extraction(
        cls,
        extraction: QuotationExtraction,
        user,
        reason: str,
    ) -> QuotationExtraction:
        """Rejects the extraction with required reason."""
        extraction.is_approved = False
        extraction.review_status = ReviewStatus.REJECTED
        extraction.reviewed_by = user
        extraction.reviewed_at = timezone.now()
        extraction.review_notes = reason
        extraction.save(update_fields=['is_approved', 'review_status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'])
        logger.info("Extraction #%s rejected by %s: %s", extraction.id, getattr(user, 'email', str(user)), reason)
        return extraction
