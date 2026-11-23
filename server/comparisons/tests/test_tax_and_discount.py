"""
Unit tests for Tax and Discount Normalization.
Verifies:
- Percent tax vs Fixed tax amounts (18% GST vs $150.00 fixed tax).
- Tax-inclusive vs Tax-exclusive pricing extraction.
- Percent discount vs Fixed lump-sum discount.
- Exempt and Reverse Charge jurisdictions.
"""
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.tax_and_discount import (
    TaxTreatment,
    DiscountTreatment,
    normalize_discount,
    normalize_tax,
)


class TaxAndDiscountNormalizationTestCase(TestCase):
    def test_percent_tax_versus_fixed_tax_amount(self):
        """Percent tax (18% GST) vs Fixed tax ($180.00 on $1,000 subtotal)."""
        subtotal = Decimal('1000.00')

        # 1. Percent Tax: 18% GST -> tax_amount = $180.00
        tax_pct = normalize_tax(
            subtotal=subtotal,
            tax_rate_percent=Decimal('18.0'),
            tax_name_or_clause='18% GST',
        )
        self.assertEqual(tax_pct.treatment, TaxTreatment.PERCENTAGE)
        self.assertEqual(tax_pct.rate_percent, Decimal('18.0'))
        self.assertEqual(tax_pct.tax_amount, Decimal('180.00'))
        self.assertEqual(tax_pct.taxable_base_amount, subtotal)

        # 2. Fixed Tax: $150.00 fixed on $1,000.00 -> derived rate = 15.00%
        tax_fixed = normalize_tax(
            subtotal=subtotal,
            stated_tax_amount=Decimal('150.00'),
            tax_name_or_clause='Fixed VAT charge',
        )
        self.assertEqual(tax_fixed.treatment, TaxTreatment.FIXED_AMOUNT)
        self.assertEqual(tax_fixed.tax_amount, Decimal('150.00'))
        self.assertEqual(tax_fixed.rate_percent, Decimal('15.00'))

    def test_tax_inclusive_extraction(self):
        """Tax inclusive extraction: $1,180.00 gross with 18% tax -> net base $1,000.00, tax $180.00."""
        gross_subtotal = Decimal('1180.00')
        tax_inc = normalize_tax(
            subtotal=gross_subtotal,
            tax_rate_percent=Decimal('18.0'),
            tax_name_or_clause='Prices inclusive of 18% GST',
            is_inclusive=True,
        )
        self.assertEqual(tax_inc.treatment, TaxTreatment.TAX_INCLUSIVE)
        self.assertEqual(tax_inc.taxable_base_amount, Decimal('1000.00'))
        self.assertEqual(tax_inc.tax_amount, Decimal('180.00'))
        self.assertTrue(tax_inc.is_inclusive)

    def test_tax_exempt_and_reverse_charge(self):
        """Tax exempt and reverse charge handling."""
        tax_exempt = normalize_tax(
            subtotal=Decimal('5000.00'),
            tax_name_or_clause='Export supply - Tax Exempt',
        )
        self.assertEqual(tax_exempt.treatment, TaxTreatment.EXEMPT)
        self.assertEqual(tax_exempt.tax_amount, Decimal('0.00'))

        tax_rcm = normalize_tax(
            subtotal=Decimal('5000.00'),
            tax_name_or_clause='Reverse charge mechanism applicable',
        )
        self.assertEqual(tax_rcm.treatment, TaxTreatment.REVERSE_CHARGE)
        self.assertEqual(tax_rcm.tax_amount, Decimal('0.00'))

    def test_discount_percent_versus_fixed(self):
        """Percent discount (5%) vs Fixed amount discount ($500.00)."""
        gross = Decimal('5000.00')

        # 5% discount on 5000 = $250.00
        disc_pct = normalize_discount(
            gross_amount=gross,
            discount_rate_percent=Decimal('5.0'),
        )
        self.assertEqual(disc_pct.treatment, DiscountTreatment.PERCENTAGE)
        self.assertEqual(disc_pct.rate_percent, Decimal('5.0'))
        self.assertEqual(disc_pct.discount_amount, Decimal('250.00'))

        # Fixed discount of $500 on 5000 -> 10.00%
        disc_fixed = normalize_discount(
            gross_amount=gross,
            stated_discount_amount=Decimal('500.00'),
        )
        self.assertEqual(disc_fixed.treatment, DiscountTreatment.FIXED_AMOUNT)
        self.assertEqual(disc_fixed.discount_amount, Decimal('500.00'))
        self.assertEqual(disc_fixed.rate_percent, Decimal('10.00'))
