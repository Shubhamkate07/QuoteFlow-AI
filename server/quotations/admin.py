from django.contrib import admin
from quotations.models import Quotation, QuotationItem, QuotationDocument, DocumentExtractionResult
from quotations.processing import DocumentProcessingService


class QuotationDocumentInline(admin.TabularInline):
    model = QuotationDocument
    extra = 0
    fields = (
        'original_filename',
        'file_type',
        'file_size',
        'mime_type',
        'processing_status',
        'processing_progress',
        'created_at',
    )
    readonly_fields = ('file_size', 'mime_type', 'created_at')
    show_change_link = True


class QuotationItemInline(admin.StackedInline):
    model = QuotationItem
    extra = 1
    fields = (
        ('position', 'rfq_item', 'match_type'),
        ('description', 'manufacturer', 'model'),
        ('quantity', 'unit', 'unit_price'),
        ('discount', 'tax', 'line_total'),
        ('lead_time_days',),
        'specifications',
        'notes',
    )
    show_change_link = True


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'quotation_number',
        'supplier',
        'rfq',
        'organization',
        'status',
        'currency',
        'total_amount',
        'quotation_date',
        'validity_date',
        'created_at',
    )
    list_filter = (
        'status',
        'currency',
        'organization',
        'quotation_date',
        'validity_date',
    )
    search_fields = (
        'quotation_number',
        'supplier__company_name',
        'rfq__rfq_number',
        'rfq__title',
        'notes',
    )
    ordering = ('-created_at',)
    inlines = [QuotationItemInline, QuotationDocumentInline]
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Tenant & Associations', {
            'fields': ('organization', 'rfq', 'supplier', 'quotation_number', 'created_by')
        }),
        ('Status & Validity', {
            'fields': ('status', 'quotation_date', 'validity_date', 'lead_time_weeks')
        }),
        ('Commercial Terms', {
            'fields': ('currency', 'delivery_terms', 'payment_terms', 'warranty_information')
        }),
        ('Financial Totals', {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        ('Documentation & Notes', {
            'fields': ('document', 'notes')
        }),
        ('System Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['recalculate_quotation_totals']

    @admin.action(description="Recalculate financial totals from line items")
    def recalculate_quotation_totals(self, request, queryset):
        count = 0
        for quotation in queryset:
            quotation.recalculate_totals(save=True)
            count += 1
        self.message_user(request, f"Successfully recalculated totals for {count} quotation(s).")


@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
    list_display = (
        'quotation',
        'position',
        'description',
        'match_type',
        'rfq_item',
        'quantity',
        'unit',
        'unit_price',
        'discount',
        'tax',
        'line_total',
    )
    list_filter = (
        'match_type',
        'unit',
        'quotation__organization',
        'quotation__status',
    )
    search_fields = (
        'description',
        'manufacturer',
        'model',
        'quotation__quotation_number',
        'quotation__supplier__company_name',
    )
    ordering = ('quotation', 'position')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(QuotationDocument)
class QuotationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'original_filename',
        'quotation',
        'organization',
        'file_type',
        'file_size_display',
        'mime_type',
        'processing_status',
        'uploaded_by',
        'created_at',
    )
    list_filter = (
        'file_type',
        'processing_status',
        'organization',
        'created_at',
    )
    search_fields = (
        'original_filename',
        'quotation__quotation_number',
        'checksum_sha256',
    )
    readonly_fields = (
        'id',
        'file_size',
        'file_size_display',
        'mime_type',
        'checksum_sha256',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)
    actions = ['trigger_text_extraction']

    @admin.action(description="Trigger text extraction (PyMuPDF / openpyxl)")
    def trigger_text_extraction(self, request, queryset):
        success_count = 0
        error_count = 0
        for doc in queryset:
            try:
                DocumentProcessingService.process_quotation_document(doc)
                success_count += 1
            except Exception as e:
                error_count += 1
        self.message_user(
            request,
            f"Extraction completed: {success_count} succeeded, {error_count} failed."
        )


@admin.register(DocumentExtractionResult)
class DocumentExtractionResultAdmin(admin.ModelAdmin):
    list_display = (
        'document',
        'document_type',
        'pages_or_sheets_count',
        'word_count',
        'character_count',
        'is_scanned_or_low_text',
        'was_ocr_performed',
        'ocr_confidence',
        'processing_time_ms',
        'created_at',
    )
    list_filter = (
        'document_type',
        'is_scanned_or_low_text',
        'was_ocr_performed',
        'organization',
        'created_at',
    )
    search_fields = (
        'document__original_filename',
        'raw_text',
        'low_text_reason',
    )
    readonly_fields = (
        'id',
        'document',
        'organization',
        'document_type',
        'pages_or_sheets_count',
        'character_count',
        'word_count',
        'is_scanned_or_low_text',
        'low_text_reason',
        'was_ocr_performed',
        'ocr_confidence',
        'processing_time_ms',
        'metadata',
        'extraction_warnings',
        'raw_text',
        'structured_content',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)
