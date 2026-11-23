"""
Serializers for AI Quotation Extractions and Human-Review Workflows in QuoteFlow AI.
Serializes validated structured data, evidence mappings, arithmetic audit metrics,
human corrections, review states, and audit trails.
"""

from rest_framework import serializers
from extractions.models import (
    CorrectionType,
    ExtractionStatus,
    QuotationExtraction,
    QuotationExtractionCorrection,
    ReviewStatus,
)


class QuotationExtractionCorrectionSerializer(serializers.ModelSerializer):
    """Serializer for individual field corrections made by human reviewers."""
    corrected_by_email = serializers.EmailField(source='corrected_by.email', read_only=True, default=None)
    extraction_id = serializers.UUIDField(source='extraction.id', read_only=True)

    class Meta:
        model = QuotationExtractionCorrection
        fields = [
            'id',
            'extraction_id',
            'correction_type',
            'field_path',
            'previous_value',
            'new_value',
            'reason',
            'corrected_by_email',
            'created_at',
        ]


class QuotationExtractionListSerializer(serializers.ModelSerializer):
    """Summary serializer for listing quotation extractions."""
    document_id = serializers.UUIDField(source='document.id', read_only=True)
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)
    quotation_id = serializers.UUIDField(source='quotation.id', read_only=True, default=None)

    class Meta:
        model = QuotationExtraction
        fields = [
            'id',
            'document_id',
            'document_filename',
            'quotation_id',
            'status',
            'review_status',
            'is_approved',
            'supplier_name',
            'quotation_number',
            'quotation_date',
            'validity_date',
            'currency',
            'stated_grand_total',
            'calculated_grand_total',
            'items_count',
            'is_math_consistent',
            'has_human_corrections',
            'corrections_count',
            'overall_confidence',
            'is_applied_to_quotation',
            'created_at',
            'updated_at',
        ]


class QuotationExtractionSerializer(serializers.ModelSerializer):
    """Detailed serializer with full line items, evidence citations, audit report, and review status."""
    document_id = serializers.UUIDField(source='document.id', read_only=True)
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)
    quotation_id = serializers.UUIDField(source='quotation.id', read_only=True, default=None)
    applied_by_email = serializers.EmailField(source='applied_by.email', read_only=True, default=None)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, default=None)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True, default=None)
    validation_flags = serializers.ListField(read_only=True)
    recent_corrections = QuotationExtractionCorrectionSerializer(source='corrections', many=True, read_only=True)

    class Meta:
        model = QuotationExtraction
        fields = [
            'id',
            'document_id',
            'document_filename',
            'quotation_id',
            'status',
            'review_status',
            'is_approved',
            'model_name',
            'supplier_name',
            'quotation_number',
            'contact_person',
            'contact_email',
            'contact_phone',
            'supplier_address',
            'quotation_date',
            'validity_date',
            'currency',
            'delivery_time',
            'delivery_terms',
            'payment_terms',
            'warranty',
            'notes',
            'stated_subtotal',
            'stated_tax',
            'stated_discount',
            'stated_shipping',
            'stated_grand_total',
            'calculated_items_subtotal',
            'calculated_grand_total',
            'total_variance',
            'is_math_consistent',
            'validation_warnings',
            'validation_flags',
            'items_count',
            'overall_confidence',
            'processing_time_ms',
            'task_id',
            'error_message',
            'reviewed_by_email',
            'reviewed_at',
            'approved_by_email',
            'approved_at',
            'review_notes',
            'reviewed_fields',
            'has_human_corrections',
            'corrections_count',
            'recent_corrections',
            'is_applied_to_quotation',
            'applied_at',
            'applied_by_email',
            'extracted_data',
            'original_extracted_data',
            'created_at',
            'updated_at',
        ]


class QuotationExtractionReviewUpdateSerializer(serializers.Serializer):
    """
    Serializer for human reviewer updates and corrections to extracted quotation data.
    Supports editing supplier info, quotation totals, commercial terms, and line items.
    """
    supplier = serializers.DictField(required=False, help_text="Updated supplier contact/address dictionary")
    quotation = serializers.DictField(required=False, help_text="Updated quotation header / financial totals dictionary")
    commercial_terms = serializers.DictField(required=False, help_text="Updated commercial, delivery, warranty conditions")
    line_items = serializers.ListField(child=serializers.DictField(), required=False, help_text="Updated list of line items")
    reason = serializers.CharField(required=False, allow_blank=True, default="", help_text="Reviewer explanation for the correction")
    mark_reviewed = serializers.BooleanField(required=False, default=True, help_text="Automatically add edited fields to reviewed_fields")


class MarkFieldsReviewedSerializer(serializers.Serializer):
    """Serializer for explicitly marking field paths as verified by reviewer."""
    fields = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        help_text="List of dot-notated field paths e.g. ['supplier.supplier_name', 'line_items[0].unit_price']",
    )


class ApproveExtractionSerializer(serializers.Serializer):
    """Serializer for approving an AI extraction for official commercial execution."""
    review_notes = serializers.CharField(required=False, allow_blank=True, default="", help_text="Approval remarks or sign-off notes")
    apply_to_quotation = serializers.BooleanField(default=False, help_text="Synchronize approved data to Quotation immediately upon approval")


class RejectExtractionSerializer(serializers.Serializer):
    """Serializer for rejecting an AI extraction."""
    reason = serializers.CharField(required=True, allow_blank=False, help_text="Required explanation for why this extraction is rejected")


class ApplyExtractionSerializer(serializers.Serializer):
    """Serializer for applying AI extraction to official Quotation."""
    replace_items = serializers.BooleanField(default=True, help_text="Replace any existing line items on the quotation")


class TriggerExtractionSerializer(serializers.Serializer):
    """Serializer for triggering AI extraction."""
    sync = serializers.BooleanField(default=False, help_text="Run synchronously in HTTP response instead of background task")
    model = serializers.CharField(required=False, default=None, help_text="Specific Gemini model override")
