"""
Django admin configuration for Quotation AI Extractions and Human Review Corrections.
"""

from django.contrib import admin
from extractions.models import QuotationExtraction, QuotationExtractionCorrection


class QuotationExtractionCorrectionInline(admin.TabularInline):
    model = QuotationExtractionCorrection
    extra = 0
    readonly_fields = ['correction_type', 'field_path', 'previous_value', 'new_value', 'reason', 'corrected_by', 'created_at']
    can_delete = False


@admin.register(QuotationExtraction)
class QuotationExtractionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'supplier_name',
        'quotation_number',
        'status',
        'review_status',
        'is_approved',
        'currency',
        'stated_grand_total',
        'calculated_grand_total',
        'items_count',
        'is_math_consistent',
        'has_human_corrections',
        'corrections_count',
        'is_applied_to_quotation',
        'created_at',
    ]
    list_filter = ['status', 'review_status', 'is_approved', 'has_human_corrections', 'is_math_consistent', 'is_applied_to_quotation', 'currency']
    search_fields = ['supplier_name', 'quotation_number', 'document__original_filename', 'review_notes']
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'processing_time_ms',
        'is_math_consistent',
        'calculated_items_subtotal',
        'calculated_grand_total',
        'total_variance',
        'reviewed_by',
        'reviewed_at',
        'approved_by',
        'approved_at',
        'corrections_count',
        'has_human_corrections',
    ]
    inlines = [QuotationExtractionCorrectionInline]


@admin.register(QuotationExtractionCorrection)
class QuotationExtractionCorrectionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'extraction',
        'correction_type',
        'field_path',
        'previous_value',
        'new_value',
        'corrected_by',
        'created_at',
    ]
    list_filter = ['correction_type', 'created_at']
    search_fields = ['field_path', 'reason', 'extraction__supplier_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
