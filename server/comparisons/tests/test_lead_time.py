"""
Unit tests for Lead Time and Delivery Timeline Normalization.
Verifies:
- Days versus weeks conversion ("14 days" vs "2 weeks").
- Delivery ranges ("3 to 4 weeks ARO").
- Immediate / Ex-stock handling.
- Business days adjustment.
"""
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.lead_time import normalize_lead_time


class LeadTimeNormalizationTestCase(TestCase):
    def test_days_versus_weeks_normalization(self):
        """14 days and 2 weeks must normalize to the exact same calendar metrics."""
        lead_14_days = normalize_lead_time("14 days")
        lead_2_weeks = normalize_lead_time("2 weeks")

        self.assertEqual(lead_14_days.representative_days, 14)
        self.assertEqual(lead_14_days.lead_time_weeks, Decimal('2.0'))

        self.assertEqual(lead_2_weeks.representative_days, 14)
        self.assertEqual(lead_2_weeks.lead_time_weeks, Decimal('2.0'))

    def test_range_normalization(self):
        """3 to 4 weeks ARO -> min 21 days, max 28 days, conservative 4.0 weeks."""
        lead = normalize_lead_time("3 to 4 weeks ARO")
        self.assertTrue(lead.is_range)
        self.assertEqual(lead.min_days, 21)
        self.assertEqual(lead.max_days, 28)
        self.assertEqual(lead.representative_days, 28)
        self.assertEqual(lead.lead_time_weeks, Decimal('4.0'))
        self.assertIn("ARO", lead.trigger_condition)

    def test_ex_stock_and_immediate(self):
        """Ex-stock, immediate, in-stock must flag is_ex_stock=True."""
        variations = ["Ex-Stock", "Immediate dispatch", "Ready in stock", "Off-the-shelf"]
        for var in variations:
            lead = normalize_lead_time(var)
            self.assertTrue(lead.is_ex_stock, f"Failed for variant: {var}")
            self.assertLessEqual(lead.representative_days, 2)

    def test_month_normalization(self):
        """1 month -> 30 days, 4.3 weeks."""
        lead = normalize_lead_time("1 month")
        self.assertEqual(lead.representative_days, 30)
        self.assertEqual(lead.lead_time_weeks, Decimal('4.3'))

    def test_business_days_normalization(self):
        """10 business days -> 14 calendar days (10 * 7 / 5)."""
        lead = normalize_lead_time("10 business days")
        self.assertEqual(lead.representative_days, 14)
        self.assertEqual(lead.lead_time_weeks, Decimal('2.0'))
