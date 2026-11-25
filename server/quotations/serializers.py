"""
Serializers for Quotations, Line Items, and Uploaded Documents.
"""

from decimal import Decimal
from typing import Optional
from rest_framework import serializers
from quotations.models import (
    Quotation,
    QuotationItem,
    QuotationDocument,
    DocumentExtractionResult,
    QuotationStatus,
    ItemMatchType,
    DocumentFileType,
    DocumentProcessingStatus,
)


class DocumentExtractionResultSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed document text extraction results.
    """
    id = serializers.UUIDField(read_only=True)
    document_id = serializers.UUIDField(source='document.id', read_only=True)
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)

    class Meta:
        model = DocumentExtractionResult
        fields = [
            'id',
            'document_id',
            'document_filename',
            'document_type',
            'pages_or_sheets_count',
            'character_count',
            'word_count',
            'has_extractable_text',
            'is_scanned_or_low_text',
            'low_text_reason',
            'was_ocr_performed',
            'ocr_confidence',
            'extraction_warnings',
            'processing_time_ms',
            'metadata',
            'raw_text',
            'structured_content',
            'created_at',
            'updated_at',
        ]


class DocumentTaskStatusSerializer(serializers.Serializer):
    """
    Serializer for checking asynchronous document processing task status.
    """
    document_id = serializers.UUIDField()
    task_id = serializers.CharField(allow_blank=True)
    celery_status = serializers.CharField()
    processing_status = serializers.CharField()
    processing_progress = serializers.IntegerField()
    processing_error = serializers.CharField(allow_blank=True)
    has_extraction_result = serializers.BooleanField()
    extraction_result_id = serializers.UUIDField(allow_null=True)
    is_scanned_or_low_text = serializers.BooleanField()
    was_ocr_performed = serializers.BooleanField()
    ocr_confidence = serializers.FloatField(allow_null=True)
    updated_at = serializers.DateTimeField()


class QuotationDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for uploaded quotation documents metadata, download links, and extraction status.
    """
    id = serializers.UUIDField(read_only=True)
    quotation_id = serializers.UUIDField(source='quotation.id', read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    processing_status_display = serializers.CharField(source='get_processing_status_display', read_only=True)
    file_size_display = serializers.CharField(read_only=True)
    download_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True, default=None)
    has_extraction_result = serializers.SerializerMethodField()
    is_scanned_or_low_text = serializers.SerializerMethodField()
    was_ocr_performed = serializers.SerializerMethodField()
    ocr_confidence = serializers.SerializerMethodField()

    class Meta:
        model = QuotationDocument
        fields = [
            'id',
            'quotation_id',
            'original_filename',
            'file_type',
            'file_type_display',
            'file_extension',
            'file_size',
            'file_size_display',
            'mime_type',
            'checksum_sha256',
            'task_id',
            'processing_status',
            'processing_status_display',
            'processing_progress',
            'processing_error',
            'has_extraction_result',
            'is_scanned_or_low_text',
            'was_ocr_performed',
            'ocr_confidence',
            'download_url',
            'uploaded_by_email',
            'created_at',
            'updated_at',
        ]

    def get_download_url(self, obj) -> str:
        request = self.context.get('request')
        url = f"/api/quotations/documents/{obj.id}/download/"
        return request.build_absolute_uri(url) if request else url

    def get_has_extraction_result(self, obj) -> bool:
        return hasattr(obj, 'extraction_result') and obj.extraction_result is not None

    def get_is_scanned_or_low_text(self, obj) -> bool:
        if hasattr(obj, 'extraction_result') and obj.extraction_result is not None:
            return obj.extraction_result.is_scanned_or_low_text
        return False

    def get_was_ocr_performed(self, obj) -> bool:
        if hasattr(obj, 'extraction_result') and obj.extraction_result is not None:
            return obj.extraction_result.was_ocr_performed
        return False

    def get_ocr_confidence(self, obj) -> Optional[float]:
        if hasattr(obj, 'extraction_result') and obj.extraction_result is not None:
            return obj.extraction_result.ocr_confidence
        return None


class QuotationItemSerializer(serializers.ModelSerializer):
    """
    Serializer for reading quotation line items with matched RFQ item info.
    """
    id = serializers.UUIDField(read_only=True)
    quotation_id = serializers.UUIDField(source='quotation.id', read_only=True)
    rfq_item_id = serializers.UUIDField(source='rfq_item.id', read_only=True, allow_null=True)
    rfq_item_name = serializers.CharField(source='rfq_item.item_name', read_only=True, default=None)
    match_type_display = serializers.CharField(source='get_match_type_display', read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            'id',
            'quotation_id',
            'rfq_item_id',
            'rfq_item_name',
            'match_type',
            'match_type_display',
            'source',
            'position',
            'description',
            'manufacturer',
            'model',
            'quantity',
            'unit',
            'unit_price',
            'discount',
            'tax',
            'line_total',
            'specifications',
            'lead_time_days',
            'notes',
            'created_at',
            'updated_at',
        ]


class QuotationItemCreateUpdateSerializer(serializers.Serializer):
    """
    Input serializer for adding or editing a quotation line item.
    """
    rfq_item_id = serializers.UUIDField(required=False, allow_null=True)
    match_type = serializers.ChoiceField(
        choices=ItemMatchType.choices,
        required=False,
        default=ItemMatchType.EXACT,
    )
    position = serializers.IntegerField(required=False, min_value=1)
    description = serializers.CharField(required=True, max_length=2000)
    manufacturer = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    model = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    quantity = serializers.DecimalField(
        required=True,
        max_digits=14,
        decimal_places=4,
        min_value=Decimal('0.0001'),
    )
    unit = serializers.CharField(required=False, default='PCS', max_length=50)
    unit_price = serializers.DecimalField(
        required=True,
        max_digits=14,
        decimal_places=4,
        min_value=Decimal('0.0000'),
    )
    discount = serializers.DecimalField(
        required=False,
        default=Decimal('0.00'),
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.00'),
    )
    tax = serializers.DecimalField(
        required=False,
        default=Decimal('0.00'),
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.00'),
    )
    specifications = serializers.DictField(required=False, default=dict)
    lead_time_days = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        qty = attrs.get('quantity')
        price = attrs.get('unit_price')
        discount = attrs.get('discount', Decimal('0.00'))

        if qty is not None and price is not None and discount is not None:
            gross = qty * price
            if discount > gross:
                raise serializers.ValidationError({
                    'discount': 'Discount cannot exceed gross amount (quantity * unit_price).'
                })
        return attrs


class QuotationListSerializer(serializers.ModelSerializer):
    """
    Lightweight summary serializer for listing quotations.
    """
    id = serializers.UUIDField(read_only=True)
    rfq_id = serializers.UUIDField(source='rfq.id', read_only=True)
    rfq_number = serializers.CharField(source='rfq.rfq_number', read_only=True)
    rfq_title = serializers.CharField(source='rfq.title', read_only=True)
    supplier_id = serializers.UUIDField(source='supplier.id', read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0)
    documents_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Quotation
        fields = [
            'id',
            'quotation_number',
            'rfq_id',
            'rfq_number',
            'rfq_title',
            'supplier_id',
            'supplier_name',
            'status',
            'status_display',
            'currency',
            'subtotal',
            'tax_amount',
            'total_amount',
            'lead_time_weeks',
            'quotation_date',
            'validity_date',
            'is_expired',
            'items_count',
            'documents_count',
            'created_at',
            'updated_at',
        ]


class QuotationDetailSerializer(serializers.ModelSerializer):
    """
    Full quotation profile including commercial terms, line items, attached documents, and audit info.
    """
    id = serializers.UUIDField(read_only=True)
    rfq_id = serializers.UUIDField(source='rfq.id', read_only=True)
    rfq_number = serializers.CharField(source='rfq.rfq_number', read_only=True)
    rfq_title = serializers.CharField(source='rfq.title', read_only=True)
    supplier_id = serializers.UUIDField(source='supplier.id', read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    documents = QuotationDocumentSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, default=None)

    class Meta:
        model = Quotation
        fields = [
            'id',
            'quotation_number',
            'rfq_id',
            'rfq_number',
            'rfq_title',
            'supplier_id',
            'supplier_name',
            'status',
            'status_display',
            'currency',
            'delivery_terms',
            'payment_terms',
            'warranty_information',
            'lead_time_weeks',
            'subtotal',
            'tax_amount',
            'total_amount',
            'quotation_date',
            'validity_date',
            'is_expired',
            'notes',
            'document',
            'items',
            'documents',
            'created_by_email',
            'created_at',
            'updated_at',
        ]


class QuotationCreateSerializer(serializers.Serializer):
    """
    Input serializer for submitting a new quotation.
    """
    rfq_id = serializers.UUIDField(required=True)
    supplier_id = serializers.UUIDField(required=True)
    quotation_number = serializers.CharField(required=True, max_length=100)
    quotation_date = serializers.DateField(required=False, allow_null=True)
    validity_date = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, default='USD', max_length=3)
    status = serializers.ChoiceField(
        choices=QuotationStatus.choices,
        required=False,
        default=QuotationStatus.RECEIVED,
    )
    delivery_terms = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    payment_terms = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    warranty_information = serializers.CharField(required=False, allow_blank=True, default='')
    lead_time_weeks = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=1,
        min_value=Decimal('0.0'),
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = QuotationItemCreateUpdateSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        q_date = attrs.get('quotation_date')
        v_date = attrs.get('validity_date')
        if q_date and v_date and v_date < q_date:
            raise serializers.ValidationError({
                'validity_date': 'Validity date cannot be earlier than quotation date.'
            })
        return attrs


class QuotationUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating quotation commercial terms, dates, or status.
    """
    rfq_id = serializers.UUIDField(required=False)
    supplier_id = serializers.UUIDField(required=False)
    quotation_number = serializers.CharField(required=False, max_length=100)
    quotation_date = serializers.DateField(required=False, allow_null=True)
    validity_date = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, max_length=3)
    status = serializers.ChoiceField(choices=QuotationStatus.choices, required=False)
    delivery_terms = serializers.CharField(required=False, allow_blank=True, max_length=255)
    payment_terms = serializers.CharField(required=False, allow_blank=True, max_length=255)
    warranty_information = serializers.CharField(required=False, allow_blank=True)
    lead_time_weeks = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=1,
        min_value=Decimal('0.0'),
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        q_date = attrs.get('quotation_date')
        v_date = attrs.get('validity_date')
        if q_date and v_date and v_date < q_date:
            raise serializers.ValidationError({
                'validity_date': 'Validity date cannot be earlier than quotation date.'
            })
        return attrs


class QuotationUploadSerializer(serializers.Serializer):
    """
    Multipart input serializer for creating a quotation directly with an uploaded document.
    """
    rfq_id = serializers.UUIDField(required=True)
    supplier_id = serializers.UUIDField(required=True)
    file = serializers.FileField(required=True)
    quotation_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    currency = serializers.CharField(required=False, default='USD', max_length=3)
    delivery_terms = serializers.CharField(required=False, allow_blank=True, default='')
    payment_terms = serializers.CharField(required=False, allow_blank=True, default='')
    warranty_information = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
