"""
Data models for AI-powered quotation document extraction in QuoteFlow AI.
Stores validated structured extraction results, evidence mapping, arithmetic verification,
human review workflows, correction audit trails, and application states.
"""

from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from core.models import BaseModel, TenantModel


class ExtractionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    PARTIAL = 'partial', 'Partially Completed'
    FAILED = 'failed', 'Failed'


class ReviewStatus(models.TextChoices):
    UNREVIEWED = 'unreviewed', 'Unreviewed (AI Output)'
    IN_REVIEW = 'in_review', 'In Review'
    CHANGES_REQUESTED = 'changes_requested', 'Changes Requested'
    APPROVED = 'approved', 'Approved (Human Verified)'
    REJECTED = 'rejected', 'Rejected'


class CorrectionType(models.TextChoices):
    SUPPLIER = 'supplier', 'Supplier Info Correction'
    QUOTATION_HEADER = 'quotation_header', 'Quotation Header Correction'
    LINE_ITEM = 'line_item', 'Line Item Correction'
    PRICE = 'price', 'Price Correction'
    QUANTITY = 'quantity', 'Quantity Correction'
    SPECIFICATION = 'specification', 'Specification Correction'
    COMMERCIAL_TERMS = 'commercial_terms', 'Commercial Terms Correction'
    TAX_SHIPPING = 'tax_shipping', 'Tax or Shipping Correction'
    OTHER = 'other', 'Other Correction'


class QuotationExtraction(TenantModel):
    """
    Stores AI-extracted commercial data from a QuotationDocument.
    Keeps extracted data decoupled from official business records until verified.
    Distinguishes pristine AI output from human-verified and approved data.
    """
    document = models.ForeignKey(
        'quotations.QuotationDocument',
        on_delete=models.CASCADE,
        related_name='ai_extractions',
        db_index=True,
        help_text="The source document analyzed by the AI model",
    )
    quotation = models.ForeignKey(
        'quotations.Quotation',
        on_delete=models.CASCADE,
        related_name='ai_extractions',
        null=True,
        blank=True,
        db_index=True,
        help_text="Target quotation record associated with this extraction",
    )
    status = models.CharField(
        max_length=32,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
        db_index=True,
        help_text="Extraction lifecycle state",
    )
    model_name = models.CharField(
        max_length=100,
        default='gemini-3.5-flash-lite',
        help_text="Gemini model version used for extraction",
    )
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Active working JSON data (reflects current verified state)",
    )
    original_extracted_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Immutable pristine snapshot of initial AI extraction before any human corrections",
    )
    raw_ai_response = models.TextField(
        blank=True,
        help_text="Raw unedited response string returned by the Gemini API",
    )

    # 1. Extracted Supplier Information (High-level summary for indexing & search)
    supplier_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Supplier or vendor company name extracted from document",
    )
    quotation_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Quotation reference, quote #, or proposal identifier",
    )
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=100, blank=True)
    supplier_address = models.TextField(blank=True)

    # 2. Extracted Quotation & Commercial Details
    quotation_date = models.DateField(null=True, blank=True)
    validity_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    delivery_terms = models.CharField(max_length=255, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    delivery_time = models.CharField(max_length=255, blank=True)
    warranty = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # 3. Financial Totals (Stated on document / verified)
    stated_subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Subtotal stated on the quotation document",
    )
    stated_tax = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax / VAT amount stated on the quotation document",
    )
    stated_discount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Document-level discount stated on the quotation document",
    )
    stated_shipping = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Shipping / freight / handling stated on the quotation document",
    )
    stated_grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Final grand total stated on the quotation document",
    )

    # 4. Independent Verification & Calculations (Never blindly trust AI)
    calculated_items_subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="System-calculated arithmetic sum: sum((quantity * unit_price) - discount + tax)",
    )
    calculated_grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="System-calculated total: calculated_subtotal + tax + shipping - discount",
    )
    total_variance = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Difference between stated grand total and system calculated total",
    )
    is_math_consistent = models.BooleanField(
        default=True,
        help_text="True if stated document totals match line item arithmetic within $0.05",
    )
    validation_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="Discrepancies, arithmetic mismatches, missing fields, or low confidence warnings",
    )

    # 5. Metadata & Execution Metrics
    items_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of line items extracted",
    )
    overall_confidence = models.FloatField(
        default=0.0,
        help_text="Composite confidence score between 0.0 and 1.0",
    )
    processing_time_ms = models.PositiveIntegerField(
        default=0,
        help_text="Total Gemini processing duration in milliseconds",
    )
    task_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Celery async task ID if run in background",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if extraction or validation failed",
    )

    # 6. Human-Review Workflow & Verification Audit
    review_status = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.UNREVIEWED,
        db_index=True,
        help_text="Current state in the human procurement review lifecycle",
    )
    is_approved = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if human reviewer approved extraction for procurement execution",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_quotation_extractions',
        help_text="User who conducted the review or applied corrections",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_quotation_extractions',
        help_text="Procurement manager or authorized user who approved the extraction",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        blank=True,
        help_text="Reviewer comments, approval notes, or rejection explanation",
    )
    reviewed_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of field names or line item indices explicitly verified by reviewer",
    )
    has_human_corrections = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if any value was modified from the original AI extraction",
    )
    corrections_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of logged human corrections applied to this extraction",
    )

    # 7. Quotation Application Audit
    is_applied_to_quotation = models.BooleanField(
        default=False,
        help_text="True if extracted values and line items have been synced into the official Quotation",
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_quotation_extractions',
    )

    class Meta:
        verbose_name = 'Quotation AI Extraction'
        verbose_name_plural = 'Quotation AI Extractions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'review_status']),
            models.Index(fields=['organization', 'is_approved']),
            models.Index(fields=['organization', 'document']),
            models.Index(fields=['organization', 'quotation']),
            models.Index(fields=['task_id']),
            models.Index(fields=['is_math_consistent']),
        ]

    @property
    def validation_flags(self) -> list:
        """Returns list of structured validation flag dictionaries."""
        if not self.validation_warnings:
            return []
        flags = []
        for item in self.validation_warnings:
            if isinstance(item, dict):
                flags.append(item)
            elif isinstance(item, str):
                flags.append({
                    "flag_type": "GENERAL_WARNING",
                    "severity": "WARNING",
                    "field": "quotation",
                    "expected_value": None,
                    "actual_value": None,
                    "explanation": item,
                })
        return flags

    def __str__(self):
        supplier = self.supplier_name or 'Unknown Supplier'
        return f"Extraction #{self.id} for {supplier} ({self.status}, {self.review_status})"

    def clean(self):
        super().clean()
        if self.document_id and self.organization_id:
            if self.document.organization_id != self.organization_id:
                raise ValidationError({
                    'document': 'Associated document belongs to a different organization.'
                })


class QuotationExtractionCorrection(TenantModel):
    """
    Immutable audit history log tracking individual field corrections made by human reviewers.
    Provides accountability, compliance traceability, and training feedback on AI accuracy.
    """
    extraction = models.ForeignKey(
        QuotationExtraction,
        on_delete=models.CASCADE,
        related_name='corrections',
        db_index=True,
        help_text="The parent quotation extraction being corrected",
    )
    correction_type = models.CharField(
        max_length=32,
        choices=CorrectionType.choices,
        default=CorrectionType.OTHER,
        db_index=True,
        help_text="Classification of the corrected commercial field",
    )
    field_path = models.CharField(
        max_length=255,
        db_index=True,
        help_text="JSON path of modified field (e.g. 'supplier.supplier_name', 'line_items[0].unit_price')",
    )
    previous_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Value as extracted by AI before this correction",
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Corrected value entered by human reviewer",
    )
    reason = models.TextField(
        blank=True,
        help_text="Reviewer explanation for the correction (e.g. 'OCR error on 8 vs 0', 'Wrong currency')",
    )
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotation_corrections',
        help_text="User who made this correction",
    )

    class Meta:
        verbose_name = 'Quotation Extraction Correction'
        verbose_name_plural = 'Quotation Extraction Corrections'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'extraction']),
            models.Index(fields=['extraction', 'correction_type']),
            models.Index(fields=['extraction', 'created_at']),
        ]

    def __str__(self):
        return f"Correction on {self.field_path}: {self.previous_value} -> {self.new_value}"
