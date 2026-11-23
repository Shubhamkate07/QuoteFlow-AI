"""
Unit tests for Warranty Terms Normalization.
Verifies:
- 1 year vs 12 months vs 24 months.
- Comprehensive, manufacturer, and parts-only classifications.
- Lifetime vs As-is / No warranty.
- Dual condition clauses (supply vs commissioning).
"""
from django.test import TestCase

from comparisons.normalization.warranty import (
    WarrantyType,
    normalize_warranty,
)


class WarrantyNormalizationTestCase(TestCase):
    def test_duration_normalization_months_and_years(self):
        """1 year and 12 months must resolve to 12 months, 365 days."""
        w_1yr = normalize_warranty("1 year")
        w_12mo = normalize_warranty("12 months")

        self.assertEqual(w_1yr.duration_months, 12)
        self.assertEqual(w_1yr.duration_days, 365)
        self.assertTrue(w_1yr.is_covered)

        self.assertEqual(w_12mo.duration_months, 12)
        self.assertEqual(w_12mo.duration_days, 365)

    def test_manufacturer_and_comprehensive_classification(self):
        """24 months manufacturer warranty vs 3 years comprehensive."""
        w_mfr = normalize_warranty("24 months manufacturer warranty")
        self.assertEqual(w_mfr.duration_months, 24)
        self.assertEqual(w_mfr.warranty_type, WarrantyType.MANUFACTURER)

        w_comp = normalize_warranty("3 years comprehensive warranty")
        self.assertEqual(w_comp.duration_months, 36)
        self.assertEqual(w_comp.warranty_type, WarrantyType.COMPREHENSIVE)

    def test_lifetime_versus_no_warranty(self):
        """Lifetime vs As-is / No warranty."""
        w_life = normalize_warranty("Lifetime warranty on structural frame")
        self.assertEqual(w_life.warranty_type, WarrantyType.LIFETIME)
        self.assertTrue(w_life.is_covered)

        w_none = normalize_warranty("Sold as-is, no warranty provided")
        self.assertEqual(w_none.warranty_type, WarrantyType.NO_WARRANTY)
        self.assertFalse(w_none.is_covered)
        self.assertEqual(w_none.duration_months, 0)

    def test_dual_condition_clause(self):
        """18 months from supply or 12 months from commissioning."""
        w_dual = normalize_warranty("18 months from supply or 12 months from commissioning")
        self.assertEqual(w_dual.duration_months, 12)
        self.assertTrue(w_dual.is_covered)
        self.assertIn("commissioning", w_dual.coverage_conditions)
