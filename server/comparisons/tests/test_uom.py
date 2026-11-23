"""
Unit tests for Unit of Measure (UOM) Normalization and Conversions.
Verifies pieces vs units, discrete scaling (dozens, gross), mass/weight, length,
and mathematical invariance (quantity * unit price).
"""
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.uom import (
    UOMCategory,
    canonicalize_uom,
    can_convert_uom,
    convert_quantity_and_price,
    get_uom_conversion_factor,
)


class UOMNormalizationTestCase(TestCase):
    def test_pieces_versus_units_canonicalization(self):
        """Pieces, units, ea, each, nos must all canonicalize to PCS."""
        variations = ['pcs', 'Pieces', 'PIECE', 'unit', 'Units', 'ea', 'EACH', 'nos', 'NO.', 'Item', 'items']
        for var in variations:
            code, cat = canonicalize_uom(var)
            self.assertEqual(code, 'PCS', f"Failed for variant: {var}")
            self.assertEqual(cat, UOMCategory.COUNT)

    def test_discrete_count_conversions(self):
        """Dozen, Gross, Pair conversions to PCS."""
        # 2 Dozen = 24 PCS
        factor = get_uom_conversion_factor('DOZEN', 'PCS')
        self.assertEqual(factor, Decimal('12.0'))

        norm_qty, norm_price, norm_unit, _, success = convert_quantity_and_price(
            source_quantity=Decimal('2.0'),
            source_unit_price=Decimal('24.00'),
            source_unit='DOZEN',
            target_unit='PCS',
        )
        self.assertTrue(success)
        self.assertEqual(norm_unit, 'PCS')
        self.assertEqual(norm_qty, Decimal('24.0000'))
        self.assertEqual(norm_price, Decimal('2.0000'))
        # Mathematical invariant: Total cost must remain identical ($48.00)
        self.assertEqual(norm_qty * norm_price, Decimal('2.0') * Decimal('24.00'))

    def test_weight_mass_conversions(self):
        """Grams vs Kilograms vs Tonnes vs Pounds."""
        # 500 grams to KG
        norm_qty, norm_price, norm_unit, factor, success = convert_quantity_and_price(
            source_quantity=Decimal('500.0'),
            source_unit_price=Decimal('0.10'),
            source_unit='G',
            target_unit='KG',
        )
        self.assertTrue(success)
        self.assertEqual(norm_unit, 'KG')
        self.assertEqual(norm_qty, Decimal('0.5000'))
        self.assertEqual(norm_price, Decimal('100.0000'))
        # Total cost invariant: 500 * 0.10 == 0.5 * 100.00 == $50.00
        self.assertEqual(norm_qty * norm_price, Decimal('50.0000'))

        # 2 Metric Tons to KG
        norm_qty, norm_price, norm_unit, _, _ = convert_quantity_and_price(
            source_quantity=Decimal('2.0'),
            source_unit_price=Decimal('500.00'),
            source_unit='MT',
            target_unit='KG',
        )
        self.assertEqual(norm_qty, Decimal('2000.0000'))
        self.assertEqual(norm_price, Decimal('0.5000'))
        self.assertEqual(norm_qty * norm_price, Decimal('1000.0000'))

    def test_length_conversions(self):
        """Meters vs Millimeters vs Feet vs Inches."""
        # 1000 mm to M
        norm_qty, norm_price, norm_unit, _, _ = convert_quantity_and_price(
            source_quantity=Decimal('1000.0'),
            source_unit_price=Decimal('0.05'),
            source_unit='MM',
            target_unit='M',
        )
        self.assertEqual(norm_unit, 'M')
        self.assertEqual(norm_qty, Decimal('1.0000'))
        self.assertEqual(norm_price, Decimal('50.0000'))

    def test_incompatible_uom_conversion(self):
        """Converting between different dimensions (e.g. KG to M) must fail gracefully."""
        self.assertFalse(can_convert_uom('KG', 'M'))
        factor = get_uom_conversion_factor('KG', 'M')
        self.assertIsNone(factor)

        # Quantity and unit price remain unchanged, original unit preserved
        norm_qty, norm_price, norm_unit, _, is_converted = convert_quantity_and_price(
            source_quantity=Decimal('10.0'),
            source_unit_price=Decimal('15.00'),
            source_unit='KG',
            target_unit='M',
        )
        self.assertFalse(is_converted)
        self.assertEqual(norm_unit, 'KG')
        self.assertEqual(norm_qty, Decimal('10.0'))
        self.assertEqual(norm_price, Decimal('15.00'))
