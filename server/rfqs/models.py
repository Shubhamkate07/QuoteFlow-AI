import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from core.models import BaseModel, TenantModel


class RFQStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    OPEN = 'open', 'Open'
    UNDER_REVIEW = 'under_review', 'Under Review'
    AWARDED = 'awarded', 'Awarded'
    CLOSED = 'closed', 'Closed'
    CANCELLED = 'cancelled', 'Cancelled'


class SpecificationImportance(models.TextChoices):
    MANDATORY = 'mandatory', 'Mandatory (Dealbreaker)'
    PREFERRED = 'preferred', 'Preferred'
    OPTIONAL = 'optional', 'Optional'


class RFQ(TenantModel):
    """
    Represents a Request for Quotation (RFQ) created by a procurement team
    within an Organization.
    """
    rfq_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Unique human-readable reference number within the organization (e.g. RFQ-2026-001)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Descriptive title of the procurement requirement",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed project background or procurement instructions",
    )
    status = models.CharField(
        max_length=32,
        choices=RFQStatus.choices,
        default=RFQStatus.DRAFT,
        db_index=True,
    )
    required_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target required delivery date for the overall RFQ",
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        validators=[
            RegexValidator(regex='^[A-Z]{3}$', message="Currency must be a 3-letter ISO uppercase code.")
        ],
        help_text="Standard 3-letter ISO currency code (e.g. USD, EUR, INR, GBP)",
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes or terms for the procurement team",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rfqs',
    )

    class Meta:
        verbose_name = 'RFQ'
        verbose_name_plural = 'RFQs'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'rfq_number'],
                name='unique_org_rfq_number',
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.rfq_number} - {self.title} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.currency:
            self.currency = self.currency.strip().upper()


class RFQItem(BaseModel):
  """
  Represents an individual line item (Bill of Materials requirement) within an RFQ.
  """
  rfq = models.ForeignKey(
      RFQ,
      on_delete=models.CASCADE,
      related_name='items',
  )
  position = models.PositiveIntegerField(
      default=1,
      help_text="Sequential line number in the RFQ",
  )
  item_name = models.CharField(
      max_length=255,
      help_text="Name or short specification of the item",
  )
  description = models.TextField(
      blank=True,
      help_text="Detailed technical description and requirements",
  )
  quantity = models.DecimalField(
      max_digits=14,
      decimal_places=4,
      validators=[
          MinValueValidator(Decimal('0.0001'), message="Quantity must be greater than zero.")
      ],
      help_text="Required procurement quantity (supports fractional units like 15.5 kg)",
  )
  unit = models.CharField(
      max_length=50,
      default='PCS',
      help_text="Unit of measurement (e.g. PCS, UNITS, KG, METER, BOX, SET, LOT)",
  )
  target_unit_price = models.DecimalField(
      max_digits=14,
      decimal_places=2,
      null=True,
      blank=True,
      validators=[
          MinValueValidator(Decimal('0.00'), message="Target price cannot be negative.")
      ],
      help_text="Internal target/budget price per unit",
  )
  manufacturer_preference = models.CharField(
      max_length=255,
      blank=True,
      help_text="Preferred brand or OEM manufacturer",
  )
  model_preference = models.CharField(
      max_length=255,
      blank=True,
      help_text="Preferred model number or part reference",
  )
  required_delivery_date = models.DateField(
      null=True,
      blank=True,
      help_text="Item-specific required delivery date (defaults to RFQ delivery date if omitted)",
  )
  custom_specifications = models.JSONField(
      default=dict,
      blank=True,
      help_text="Arbitrary unstructured or nested technical specifications (JSON)",
  )
  notes = models.TextField(
      blank=True,
      help_text="Special line item notes, tolerances, or handling instructions",
  )

  class Meta:
      verbose_name = 'RFQ Item'
      verbose_name_plural = 'RFQ Items'
      ordering = ['rfq', 'position', 'item_name']
      constraints = [
          models.CheckConstraint(
              check=models.Q(quantity__gt=0),
              name='rfq_item_quantity_gt_zero',
          ),
      ]
      indexes = [
          models.Index(fields=['rfq', 'position']),
          models.Index(fields=['rfq', 'item_name']),
      ]

  def __str__(self):
      return f"#{self.position} {self.item_name} ({self.quantity} {self.unit})"

  @property
  def effective_delivery_date(self):
      return self.required_delivery_date or self.rfq.required_delivery_date


class RFQItemSpecification(BaseModel):
    """
    Structured technical specification attribute for an RFQ line item.
    Enables explainable AI extraction matching, scoring, and side-by-side comparison.
    """
    item = models.ForeignKey(
        RFQItem,
        on_delete=models.CASCADE,
        related_name='specifications',
    )
    parameter_name = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Technical parameter name (e.g. Operating Voltage, Tensile Strength, Material, IP Rating)",
    )
    required_value = models.CharField(
        max_length=255,
        help_text="Required value or standard (e.g. 24V DC, 500 MPa, SS 316L, IP67)",
    )
    tolerance_or_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Acceptable tolerance or measurement unit (e.g. ±5%, mm, °C)",
    )
    importance = models.CharField(
        max_length=32,
        choices=SpecificationImportance.choices,
        default=SpecificationImportance.MANDATORY,
        help_text="Criticality of the specification for scoring & risk flag evaluation",
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional clarifications or test standard reference",
    )

    class Meta:
        verbose_name = 'RFQ Item Specification'
        verbose_name_plural = 'RFQ Item Specifications'
        ordering = ['item', 'parameter_name']
        indexes = [
            models.Index(fields=['item', 'parameter_name']),
        ]

    def __str__(self):
        unit_str = f" {self.tolerance_or_unit}" if self.tolerance_or_unit else ""
        return f"{self.parameter_name}: {self.required_value}{unit_str} ({self.get_importance_display()})"
