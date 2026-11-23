"""
Unit tests for Commercial Payment Terms Normalization.
Verifies:
- Advance payment vs Credit payment terms (100% advance vs Net 30/60).
- Milestone and split payments (30% advance, 70% delivery).
- COD and Letter of Credit.
- Cash flow risk evaluation.
"""
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.payment_terms import (
    PaymentTermCategory,
    normalize_payment_terms,
)


class PaymentTermsNormalizationTestCase(TestCase):
    def test_advance_versus_net_credit_terms(self):
        """100% advance vs Net 30 Days."""
        advance = normalize_payment_terms("100% Advance Payment")
        self.assertEqual(advance.category, PaymentTermCategory.ADVANCE)
        self.assertEqual(advance.advance_percent, Decimal('100.0'))
        self.assertEqual(advance.credit_days, 0)
        self.assertTrue(advance.has_advance_requirement)
        self.assertEqual(advance.cash_flow_risk_score, Decimal('10.0'))

        net30 = normalize_payment_terms("Net 30 Days")
        self.assertEqual(net30.category, PaymentTermCategory.NET_CREDIT)
        self.assertEqual(net30.advance_percent, Decimal('0.0'))
        self.assertEqual(net30.credit_days, 30)
        self.assertFalse(net30.has_advance_requirement)
        self.assertEqual(net30.cash_flow_risk_score, Decimal('3.0'))

        net60 = normalize_payment_terms("Net 60 Days from invoice")
        self.assertEqual(net60.category, PaymentTermCategory.NET_CREDIT)
        self.assertEqual(net60.credit_days, 60)
        self.assertLess(net60.cash_flow_risk_score, net30.cash_flow_risk_score)

    def test_split_advance_milestones(self):
        """30% advance, 70% against dispatch."""
        split = normalize_payment_terms("30% advance, 70% on dispatch")
        self.assertEqual(split.category, PaymentTermCategory.PARTIAL_ADVANCE)
        self.assertEqual(split.advance_percent, Decimal('30.0'))
        self.assertEqual(split.credit_percent, Decimal('70.0'))
        self.assertTrue(split.has_advance_requirement)
        self.assertEqual(len(split.milestones), 2)

    def test_cash_on_delivery(self):
        """COD terms."""
        cod = normalize_payment_terms("Cash on Delivery (COD)")
        self.assertEqual(cod.category, PaymentTermCategory.COD)
        self.assertEqual(cod.advance_percent, Decimal('0.0'))
        self.assertEqual(cod.credit_days, 0)

    def test_letter_of_credit(self):
        """LC at sight."""
        lc = normalize_payment_terms("Irrevocable Letter of Credit (L/C) at sight")
        self.assertEqual(lc.category, PaymentTermCategory.LETTER_OF_CREDIT)
        self.assertEqual(lc.credit_days, 0)
