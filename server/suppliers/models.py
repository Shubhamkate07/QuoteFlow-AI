from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel


class SupplierCategory(models.TextChoices):
    MACHINING = 'machining', 'CNC Machining & Milling'
    SHEET_METAL = 'sheet_metal', 'Sheet Metal Fabrication'
    FASTENERS = 'fasteners', 'Hardware & Fasteners'
    PLASTICS = 'plastics', 'Injection Molding & Polymers'
    ELECTRONICS = 'electronics', 'PCBA & Cable Harnesses'
    RAW_MATERIALS = 'raw_materials', 'Raw Materials & Stock'
    SURFACE_TREATMENT = 'surface_treatment', 'Surface Treatment & Coating'
    OTHER = 'other', 'Other Specialized Services'


class SupplierStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PENDING = 'pending', 'Pending Approval'
    INACTIVE = 'inactive', 'Inactive'


class Supplier(BaseModel):
    """
    Supplier / Vendor entity scoped strictly to an Organization.
    Stores vendor contact details, tax compliance identifiers, category, and audit metadata.
    """
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='suppliers',
        db_index=True,
        help_text="Tenant organization that owns this supplier record",
    )
    company_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Official business or corporate entity name",
    )
    contact_person = models.CharField(
        max_length=255,
        help_text="Primary point of contact or sales representative",
    )
    email = models.EmailField(
        max_length=255,
        db_index=True,
        help_text="Primary quotation submission and inquiry email",
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Direct phone number with country/area code",
    )
    address = models.TextField(
        blank=True,
        help_text="Physical factory, warehouse, or corporate office address",
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default='US',
        db_index=True,
        help_text="Country of incorporation or manufacturing origin",
    )
    gst_vat_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="GST, VAT, EIN, or regional business tax registration identifier",
    )
    website = models.URLField(
        max_length=255,
        blank=True,
        help_text="Official website or online catalog URL",
    )
    category = models.CharField(
        max_length=50,
        choices=SupplierCategory.choices,
        default=SupplierCategory.OTHER,
        db_index=True,
        help_text="Primary manufacturing capability or supply commodity",
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes, compliance certifications (ISO 9001, AS9100), or trade credit terms",
    )
    status = models.CharField(
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.ACTIVE,
        db_index=True,
        help_text="Vendor active state in procurement directory",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal('1.00'), message="Rating cannot be less than 1.00."),
            MaxValueValidator(Decimal('5.00'), message="Rating cannot exceed 5.00."),
        ],
        help_text="Historical vendor quality & delivery score (1.00 to 5.00)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_suppliers',
        help_text="User who onboarded this vendor",
    )

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['company_name', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'company_name']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'country']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'company_name'],
                name='unique_supplier_per_organization',
            )
        ]

    def __str__(self):
        return f"{self.company_name} ({self.get_category_display()})"
