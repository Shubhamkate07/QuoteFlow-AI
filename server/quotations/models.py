import os
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from core.models import BaseModel, TenantModel


class QuotationStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    RECEIVED = 'received', 'Received'
    UNDER_REVIEW = 'under_review', 'Under Review'
    ACCEPTED = 'accepted', 'Accepted / Awarded'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class ItemMatchType(models.TextChoices):
    EXACT = 'exact', 'Exact Match'
    SUBSTITUTE = 'substitute', 'Substitute / Alternative'
    ADDITIONAL = 'additional', 'Additional / Auxiliary'
    UNMATCHED = 'unmatched', 'Unmatched'


class Quotation(TenantModel):
    """
    Represents a formal commercial quotation submitted by an approved Supplier
    in response to an RFQ within an Organization.
    """
    rfq = models.ForeignKey(
        'rfqs.RFQ',
        on_delete=models.CASCADE,
        related_name='quotations',
        db_index=True,
        help_text="Target RFQ this quotation responds to",
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.CASCADE,
        related_name='quotations',
        db_index=True,
        help_text="Vendor submitting the quotation",
    )
    quotation_number = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Supplier's internal quote reference, proposal number, or invoice identifier",
    )
    quotation_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the quote was issued by the supplier",
    )
    validity_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiration date of quoted pricing and commercial terms",
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        validators=[
            RegexValidator(regex='^[A-Z]{3}$', message="Currency must be a 3-letter ISO uppercase code.")
        ],
        help_text="3-letter ISO currency code (e.g. USD, EUR, INR, GBP)",
    )
    status = models.CharField(
        max_length=32,
        choices=QuotationStatus.choices,
        default=QuotationStatus.RECEIVED,
        db_index=True,
        help_text="Current review or procurement decision status",
    )
    delivery_terms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Delivery terms / Incoterms (e.g. FOB Shanghai, EXW, CIF Rotterdam, DDP Austin)",
    )
    payment_terms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Commercial payment terms (e.g. Net 30, Net 60, 50% advance / 50% on dispatch)",
    )
    warranty_information = models.TextField(
        blank=True,
        help_text="Warranty duration, conditions, coverage limits, and RMA policies",
    )
    lead_time_weeks = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal('0.0'), message="Lead time cannot be negative.")
        ],
        help_text="Quoted lead time in weeks from PO issuance to dispatch",
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'), message="Subtotal cannot be negative.")
        ],
        help_text="Aggregate net total of all line items before taxes",
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'), message="Tax amount cannot be negative.")
        ],
        help_text="Total tax or VAT amount across all line items",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'), message="Total amount cannot be negative.")
        ],
        help_text="Grand total quotation value (subtotal + tax)",
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal procurement notes, buyer evaluation feedback, or supplier remarks",
    )
    document = models.FileField(
        upload_to='quotations/%Y/%m/',
        max_length=500,
        null=True,
        blank=True,
        help_text="Original uploaded quotation document (PDF, Excel, or scan)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quotations',
        help_text="User who recorded or uploaded this quotation",
    )

    class Meta:
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'rfq', 'supplier', 'quotation_number'],
                name='unique_quotation_per_supplier_rfq',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(validity_date__gte=models.F('quotation_date')) |
                    models.Q(validity_date__isnull=True) |
                    models.Q(quotation_date__isnull=True)
                ),
                name='quote_validity_after_or_equal_quote_date',
            ),
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name='quote_subtotal_gte_zero',
            ),
            models.CheckConstraint(
                check=models.Q(tax_amount__gte=0),
                name='quote_tax_gte_zero',
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name='quote_total_amount_gte_zero',
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'rfq']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['rfq', 'supplier']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        supplier_name = self.supplier.company_name if self.supplier_id else 'Unknown Supplier'
        return f"{self.quotation_number} - {supplier_name} ({self.currency} {self.total_amount})"

    def clean(self):
        super().clean()
        if self.currency:
            self.currency = self.currency.strip().upper()

        if self.quotation_date and self.validity_date:
            if self.validity_date < self.quotation_date:
                raise ValidationError({
                    'validity_date': 'Validity date cannot be earlier than quotation date.'
                })

        # Tenant boundary safety: RFQ and Supplier must belong to the exact same organization
        if self.rfq_id and self.organization_id:
            if self.rfq.organization_id != self.organization_id:
                raise ValidationError({
                    'rfq': 'Selected RFQ does not belong to your organization.'
                })

        if self.supplier_id and self.organization_id:
            if self.supplier.organization_id != self.organization_id:
                raise ValidationError({
                    'supplier': 'Selected Supplier does not belong to your organization.'
                })

    @property
    def is_expired(self) -> bool:
        if self.validity_date:
            return self.validity_date < timezone.now().date()
        return False

    def recalculate_totals(self, save: bool = True):
        """
        Recalculates subtotal, tax_amount, and total_amount from all associated line items.
        """
        if hasattr(self, '_prefetched_objects_cache') and 'items' in self._prefetched_objects_cache:
            del self._prefetched_objects_cache['items']
        items = self.items.all()
        calculated_subtotal = Decimal('0.00')
        calculated_tax = Decimal('0.00')

        for item in items:
            calculated_subtotal += (item.quantity * item.unit_price) - item.discount
            calculated_tax += item.tax

        self.subtotal = max(Decimal('0.00'), calculated_subtotal)
        self.tax_amount = max(Decimal('0.00'), calculated_tax)
        self.total_amount = self.subtotal + self.tax_amount

        if save:
            self.save(update_fields=['subtotal', 'tax_amount', 'total_amount', 'updated_at'])


class QuotationItem(BaseModel):
    """
    Represents an individual line item quoted by a supplier.
    Supports 1:1 RFQ mapping, substitute items, and auxiliary/additional items
    (such as tooling, packaging, testing, or unprompted accessories).
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='items',
        db_index=True,
    )
    rfq_item = models.ForeignKey(
        'rfqs.RFQItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotation_items',
        db_index=True,
        help_text="Mapped RFQ line item. Null if supplier quoted an extra or unsolicited item.",
    )
    match_type = models.CharField(
        max_length=32,
        choices=ItemMatchType.choices,
        default=ItemMatchType.EXACT,
        db_index=True,
        help_text="Relationship classification to RFQ requirement (exact, substitute, additional, unmatched)",
    )
    position = models.PositiveIntegerField(
        default=1,
        help_text="Line item position in the supplier quotation",
    )
    description = models.TextField(
        help_text="Quoted product description, specification summary, or service name",
    )
    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        help_text="Quoted manufacturer, brand, or OEM fabricator",
    )
    model = models.CharField(
        max_length=255,
        blank=True,
        help_text="Quoted part number, catalog number, or model designation",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal('0.0001'), message="Quantity must be greater than zero.")
        ],
        help_text="Quoted quantity (supports fractional units like 25.5 kg)",
    )
    unit = models.CharField(
        max_length=50,
        default='PCS',
        help_text="Unit of measurement (e.g. PCS, METER, KG, BOX, SET, LOT)",
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal('0.0000'), message="Unit price cannot be negative.")
        ],
        help_text="Price per unit before discounts and taxes",
    )
    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'), message="Discount cannot be negative.")
        ],
        help_text="Total promotional or volume discount applied to this line item",
    )
    tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00'), message="Tax cannot be negative.")
        ],
        help_text="Tax or VAT amount applicable to this line item",
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.00'), message="Line total cannot be negative.")
        ],
        help_text="Net line total: (quantity * unit_price) - discount + tax",
    )
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text="Technical specifications and parameters quoted by supplier (JSON key-value pairs)",
    )
    lead_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Item-specific production or dispatch lead time in calendar days",
    )
    notes = models.TextField(
        blank=True,
        help_text="Line item notes, minimum order quantity (MOQ) caveats, or technical exceptions",
    )

    class Meta:
        verbose_name = 'Quotation Item'
        verbose_name_plural = 'Quotation Items'
        ordering = ['quotation', 'position']
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name='quote_item_quantity_gt_zero',
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name='quote_item_unit_price_gte_zero',
            ),
            models.CheckConstraint(
                check=models.Q(discount__gte=0),
                name='quote_item_discount_gte_zero',
            ),
            models.CheckConstraint(
                check=models.Q(tax__gte=0),
                name='quote_item_tax_gte_zero',
            ),
            models.CheckConstraint(
                check=models.Q(line_total__gte=0),
                name='quote_item_line_total_gte_zero',
            ),
        ]
        indexes = [
            models.Index(fields=['quotation', 'position']),
            models.Index(fields=['quotation', 'rfq_item']),
            models.Index(fields=['rfq_item']),
            models.Index(fields=['match_type']),
        ]

    def __str__(self):
        return f"Quote #{self.quotation.quotation_number} - Item #{self.position}: {self.description[:40]}"

    def calculate_line_total(self) -> Decimal:
        """
        Calculates (quantity * unit_price) - discount + tax rounded to 2 decimal places.
        """
        qty = self.quantity or Decimal('0.00')
        price = self.unit_price or Decimal('0.00')
        disc = self.discount or Decimal('0.00')
        tx = self.tax or Decimal('0.00')
        subtotal = (qty * price) - disc
        return max(Decimal('0.00'), (subtotal + tx).quantize(Decimal('0.01')))

    def clean(self):
        super().clean()
        if self.discount is not None and self.quantity is not None and self.unit_price is not None:
            gross = self.quantity * self.unit_price
            if self.discount > gross:
                raise ValidationError({
                    'discount': 'Discount cannot exceed gross line item amount (quantity * unit_price).'
                })

        # Multi-tenant and RFQ alignment check
        if self.rfq_item_id and self.quotation_id:
            if self.rfq_item.rfq_id != self.quotation.rfq_id:
                raise ValidationError({
                    'rfq_item': 'The selected RFQ item does not belong to the quotation\'s RFQ.'
                })

    def save(self, *args, **kwargs):
        # Auto-compute line_total if not manually provided or if recalculation needed
        if self.line_total is None or self.line_total == Decimal('0.00'):
            self.line_total = self.calculate_line_total()
        super().save(*args, **kwargs)


class DocumentFileType(models.TextChoices):
    PDF = 'pdf', 'PDF Document'
    EXCEL = 'excel', 'Excel Spreadsheet'
    IMAGE = 'image', 'Image (PNG/JPG)'


class DocumentProcessingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Processing'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Processing Failed'


def quotation_document_upload_path(instance, filename):
    """
    Generates a secure, non-guessable, path-traversal-free storage path.
    Format: quotations/documents/<org_id>/<year>/<month>/<uuid>.<safe_ext>
    The client-supplied filename is never trusted or used on the filesystem.
    """
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if not ext or ext not in ('pdf', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'):
        ext = instance.file_extension if hasattr(instance, 'file_extension') and instance.file_extension else 'dat'
    file_uuid = uuid.uuid4().hex
    org_id = str(instance.organization_id)
    now = timezone.now()
    return f"quotations/documents/{org_id}/{now.year:04d}/{now.month:02d}/{file_uuid}.{ext}"


class QuotationDocument(TenantModel):
    """
    Stores uploaded supplier quotation files (PDF, XLSX, PNG, JPG).
    Enforces tenant boundaries, file size limits, MIME integrity,
    and maintains processing status for automated extraction.
    """
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='documents',
        db_index=True,
        help_text="Parent quotation this document belongs to",
    )
    file = models.FileField(
        upload_to=quotation_document_upload_path,
        max_length=500,
        help_text="Path to physically stored document on disk",
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original uploaded filename (sanitized for display)",
    )
    file_type = models.CharField(
        max_length=32,
        choices=DocumentFileType.choices,
        db_index=True,
        help_text="Document format category (PDF, Excel, or Image)",
    )
    file_extension = models.CharField(
        max_length=16,
        help_text="File extension without dot (e.g. pdf, xlsx, png, jpg)",
    )
    file_size = models.PositiveBigIntegerField(
        help_text="File size in bytes",
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="Validated MIME type",
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Cryptographic SHA-256 hash of file content for integrity and deduplication",
    )
    processing_status = models.CharField(
        max_length=32,
        choices=DocumentProcessingStatus.choices,
        default=DocumentProcessingStatus.PENDING,
        db_index=True,
        help_text="Document parsing and AI extraction lifecycle status",
    )
    processing_progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="Processing or extraction progress percentage (0 - 100)",
    )
    processing_error = models.TextField(
        blank=True,
        help_text="Detailed failure reason if processing or AI extraction fails",
    )
    task_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Celery async task ID for document processing",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_quotation_documents',
        help_text="User who uploaded this document",
    )

    class Meta:
        verbose_name = 'Quotation Document'
        verbose_name_plural = 'Quotation Documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'processing_status']),
            models.Index(fields=['organization', 'quotation']),
            models.Index(fields=['quotation', 'created_at']),
            models.Index(fields=['checksum_sha256']),
            models.Index(fields=['task_id']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.file_size_display}) - {self.get_processing_status_display()}"

    @property
    def file_size_display(self) -> str:
        """Human-readable file size string (e.g. 2.4 MB, 450 KB)."""
        size = float(self.file_size or 0)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} B"
            size /= 1024.0
        return f"{size:.1f} TB"

    def clean(self):
        super().clean()
        if self.quotation_id and self.organization_id:
            if self.quotation.organization_id != self.organization_id:
                raise ValidationError({
                    'quotation': 'Associated quotation belongs to a different organization.'
                })


class DocumentExtractionResult(TenantModel):
    """
    Stores structured text extraction results from uploaded quotation documents.
    Preserves page-by-page (PDF) and worksheet-by-worksheet (Excel) content,
    tracks text density metrics, and flags scanned/image documents for subsequent OCR.
    """
    document = models.OneToOneField(
        QuotationDocument,
        on_delete=models.CASCADE,
        related_name='extraction_result',
        db_index=True,
        help_text="The source quotation document that was parsed",
    )
    document_type = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Document type extracted ('pdf' or 'excel')",
    )
    raw_text = models.TextField(
        blank=True,
        help_text="Full consolidated extracted text from all pages or worksheets",
    )
    pages_or_sheets_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of pages (PDF) or worksheets (Excel)",
    )
    character_count = models.PositiveIntegerField(
        default=0,
        help_text="Total character count extracted",
    )
    word_count = models.PositiveIntegerField(
        default=0,
        help_text="Total word count extracted",
    )
    structured_content = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured page-by-page or sheet-by-sheet JSON payload",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Document metadata (title, author, creation date, dimensions, sheet names)",
    )
    has_extractable_text = models.BooleanField(
        default=True,
        help_text="True if any digital text was extracted from the document",
    )
    is_scanned_or_low_text = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if document has little or no extractable digital text (scanned PDF or blank sheet)",
    )
    low_text_reason = models.CharField(
        max_length=500,
        blank=True,
        help_text="Detailed explanation if flagged as scanned or low text",
    )
    was_ocr_performed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if OCR was executed for scanned pages or image documents",
    )
    ocr_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Average OCR confidence score percentage (0.0 to 100.0) if OCR was performed",
    )
    extraction_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="List of warnings encountered during extraction",
    )
    processing_time_ms = models.PositiveIntegerField(
        default=0,
        help_text="Duration of text extraction in milliseconds",
    )

    class Meta:
        verbose_name = 'Document Extraction Result'
        verbose_name_plural = 'Document Extraction Results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'document_type']),
            models.Index(fields=['organization', 'is_scanned_or_low_text']),
            models.Index(fields=['organization', 'was_ocr_performed']),
            models.Index(fields=['document', 'created_at']),
        ]

    def __str__(self):
        units = f"{self.pages_or_sheets_count} pages" if self.document_type == 'pdf' else f"{self.pages_or_sheets_count} sheets"
        status = "Scanned/Low-Text" if self.is_scanned_or_low_text else f"{self.word_count} words"
        return f"Extraction for {self.document.original_filename} ({units}, {status})"

    def clean(self):
        super().clean()
        if self.document_id and self.organization_id:
            if self.document.organization_id != self.organization_id:
                raise ValidationError({
                    'document': 'Associated document belongs to a different organization.'
                })


