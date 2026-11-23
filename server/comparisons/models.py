"""
Models for Quotation Comparisons, Corporate Exchange Rates, and Normalized Snapshots.
"""
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from core.models import BaseModel, TenantModel


class ExchangeRate(TenantModel):
    """
    Corporate Exchange Rate record maintained per organization.
    Ensures exchange rates are never invented or guessed:
    requires an explicit rate_source (e.g. 'ECB', 'RBI', 'Contract Fixed') and rate_date.
    """
    source_currency = models.CharField(
        max_length=3,
        validators=[RegexValidator(regex='^[A-Z]{3}$', message="Currency must be a 3-letter ISO code.")],
        db_index=True,
        help_text="Source 3-letter ISO currency code (e.g. EUR, INR, GBP)",
    )
    target_currency = models.CharField(
        max_length=3,
        validators=[RegexValidator(regex='^[A-Z]{3}$', message="Currency must be a 3-letter ISO code.")],
        db_index=True,
        help_text="Target 3-letter ISO currency code (e.g. USD, EUR, INR)",
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'), message="Exchange rate must be strictly positive.")],
        help_text="Conversion multiplier: 1 unit of source_currency = rate units of target_currency",
    )
    rate_source = models.CharField(
        max_length=255,
        help_text="Official source of the exchange rate (e.g. European Central Bank, Reserve Bank of India, Treasury Fixing)",
    )
    rate_date = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Effective date for this exchange rate",
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional treasury or contract notes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_exchange_rates',
    )

    class Meta:
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'
        ordering = ['-rate_date', 'source_currency', 'target_currency']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'source_currency', 'target_currency', 'rate_date'],
                name='unique_org_currency_pair_per_date',
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'source_currency', 'target_currency']),
            models.Index(fields=['organization', 'rate_date']),
        ]

    def __str__(self):
        return f"1 {self.source_currency} = {self.rate} {self.target_currency} ({self.rate_source} on {self.rate_date})"

    def clean(self):
        super().clean()
        if self.source_currency:
            self.source_currency = self.source_currency.strip().upper()
        if self.target_currency:
            self.target_currency = self.target_currency.strip().upper()


class NormalizedQuotationSnapshot(TenantModel):
    """
    Persisted deterministic snapshot of a normalized quotation ready for matrix comparison.
    Preserves exact UOM conversions, tax treatments, payment terms, and currency conversions.
    """
    quotation = models.ForeignKey(
        'quotations.Quotation',
        on_delete=models.CASCADE,
        related_name='normalized_snapshots',
        db_index=True,
    )
    rfq = models.ForeignKey(
        'rfqs.RFQ',
        on_delete=models.CASCADE,
        related_name='normalized_quotation_snapshots',
        db_index=True,
    )
    native_currency = models.CharField(max_length=3)
    normalized_currency = models.CharField(max_length=3)
    exchange_rate_applied = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Exchange rate multiplier applied (null if no conversion required)",
    )
    rate_source = models.CharField(max_length=255, blank=True)
    rate_date = models.DateField(null=True, blank=True)
    normalized_data = models.JSONField(
        default=dict,
        help_text="Full JSON serialization of NormalizedQuotation schema",
    )
    normalized_grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Final reconciled total in normalized_currency",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_normalized_snapshots',
    )

    class Meta:
        verbose_name = 'Normalized Quotation Snapshot'
        verbose_name_plural = 'Normalized Quotation Snapshots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'rfq']),
            models.Index(fields=['organization', 'quotation']),
        ]

    def __str__(self):
        return f"Normalized Snapshot: {self.quotation.quotation_number} ({self.normalized_currency} {self.normalized_grand_total})"


class RFQComparisonSnapshot(TenantModel):
    """
    Persisted deterministic comparison snapshot across all vendor quotations for an RFQ.
    Caches calculated price differences, rankings, cherry-pick savings, and item matrices.
    """
    rfq = models.ForeignKey(
        'rfqs.RFQ',
        on_delete=models.CASCADE,
        related_name='comparison_snapshots',
        db_index=True,
    )
    comparison_currency = models.CharField(
        max_length=3,
        help_text="Standardized ISO currency code used for this comparison run",
    )
    quotations_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of quotations included in this comparison",
    )
    lowest_grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    highest_grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    potential_savings = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    cherry_pick_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    cherry_pick_savings = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    summary_data = models.JSONField(
        default=dict,
        help_text="Full JSON serialization of RFQComparisonSummary schema",
    )
    weights_used = models.JSONField(
        default=dict,
        blank=True,
        help_text="Scoring weights configuration applied in this run",
    )
    approved_only_applied = models.BooleanField(
        default=True,
        help_text="Whether unreviewed AI extractions were excluded",
    )
    unreviewed_quotations_count = models.PositiveIntegerField(
        default=0,
        help_text="Count of active quotations excluded due to pending review/approval",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rfq_comparison_snapshots',
    )

    class Meta:
        verbose_name = 'RFQ Comparison Snapshot'
        verbose_name_plural = 'RFQ Comparison Snapshots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'rfq']),
            models.Index(fields=['organization', '-created_at']),
        ]

    def __str__(self):
        rfq_num = getattr(self.rfq, 'rfq_number', str(self.rfq_id))
        return f"Comparison Snapshot for RFQ {rfq_num} ({self.comparison_currency} {self.lowest_grand_total})"


class RFQComparisonSetting(TenantModel):
    """
    Persisted comparison preferences and multi-criteria scoring weights for an RFQ.
    Allows procurement teams to customize weights (e.g. price 40%, specs 30%, delivery 15%...)
    and policies (approved_only, comparison_currency, include_incompatible).
    """
    rfq = models.OneToOneField(
        'rfqs.RFQ',
        on_delete=models.CASCADE,
        related_name='comparison_setting',
        db_index=True,
    )
    weights = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom scoring weights: price, spec_match, delivery, payment_terms, warranty (must sum to 100%)",
    )
    comparison_currency = models.CharField(
        max_length=3,
        blank=True,
        help_text="Default comparison currency for this RFQ (defaults to RFQ.currency if empty)",
    )
    approved_only = models.BooleanField(
        default=True,
        help_text="If True, only approved or appropriately reviewed quotations are included in comparison",
    )
    include_incompatible = models.BooleanField(
        default=False,
        help_text="If True, quotations with incompatible items are included in lowest price calculation",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_rfq_comparison_settings',
    )

    class Meta:
        verbose_name = 'RFQ Comparison Setting'
        verbose_name_plural = 'RFQ Comparison Settings'
        indexes = [
            models.Index(fields=['organization', 'rfq']),
        ]

    def __str__(self):
        rfq_num = getattr(self.rfq, 'rfq_number', str(self.rfq_id))
        return f"Comparison Setting for RFQ {rfq_num}"

