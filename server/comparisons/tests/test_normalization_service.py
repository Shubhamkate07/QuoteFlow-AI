"""
Unit tests for QuotationNormalizationService end-to-end orchestration.
Verifies multi-currency quotations, target RFQ item UOM alignment, and complete normalization.
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.currency import ExchangeRate, ExchangeRateTable
from comparisons.normalization.service import QuotationNormalizationService


class QuotationNormalizationServiceTestCase(TestCase):
    def setUp(self):
        self.rate_table = ExchangeRateTable([
            ExchangeRate(
                source_currency='INR',
                target_currency='USD',
                rate=Decimal('0.01156'),  # 1 INR = $0.01156 USD (~ 86.5 INR/USD)
                rate_source='RBI Fixing Benchmark',
                rate_date=date(2026, 11, 20),
            ),
            ExchangeRate(
                source_currency='EUR',
                target_currency='USD',
                rate=Decimal('1.0850'),
                rate_source='ECB Daily Reference',
                rate_date=date(2026, 11, 20),
            ),
        ])
        self.service = QuotationNormalizationService(self.rate_table)

    def test_end_to_end_normalization_with_uom_and_terms(self):
        """Normalizes extracted payload: Dozen -> PCS, 14 days -> 2.0 weeks, 100% advance, warranty."""
        extracted = {
            'supplier': {
                'supplier_name': 'Precision Machining Co.',
                'quotation_number': 'QT-9921',
            },
            'quotation': {
                'quotation_date': '2026-11-15',
                'validity_date': '2026-12-15',
                'currency': 'USD',
                'subtotal': 1200.0,
                'tax': 120.0,
                'discount': 50.0,
                'grand_total': 1270.0,
            },
            'commercial_terms': {
                'delivery_time': '14 days',
                'payment_terms': '100% Advance Payment',
                'warranty': '24 months manufacturer warranty',
                'delivery_terms': 'FOB Detroit',
            },
            'line_items': [
                {
                    'line_number': 1,
                    'description': 'Titanium Fastener M8',
                    'quantity': 10,  # 10 Dozen
                    'unit': 'DOZEN',
                    'unit_price': 120.0,
                    'discount': 0.0,
                    'tax': 0.0,
                    'total': 1200.0,
                }
            ],
        }

        # Target RFQ requires units in PCS
        target_rfq_items = [{'id': 'rfq-item-1', 'unit': 'PCS'}]
        extracted['line_items'][0]['rfq_item_id'] = 'rfq-item-1'

        norm = self.service.normalize(extracted_data=extracted, target_rfq_items=target_rfq_items)

        # 1. Commercial Terms
        self.assertEqual(norm.commercial_terms.lead_time.representative_days, 14)
        self.assertEqual(norm.commercial_terms.lead_time.lead_time_weeks, Decimal('2.0'))
        self.assertEqual(norm.commercial_terms.payment_terms.advance_percent, Decimal('100.0'))
        self.assertEqual(norm.commercial_terms.warranty.duration_months, 24)

        # 2. Line Items UOM scaling
        self.assertEqual(len(norm.items), 1)
        item = norm.items[0]
        self.assertEqual(item.normalized_unit, 'PCS')
        self.assertEqual(item.normalized_quantity, Decimal('120.0000'))  # 10 dozen = 120 pcs
        self.assertEqual(item.normalized_unit_price, Decimal('10.0000'))  # $120/dozen = $10/pc
        self.assertEqual(item.normalized_total, Decimal('1200.00'))  # Total remains $1,200

        # 3. Financials
        self.assertEqual(norm.financials.normalized_currency, 'USD')
        self.assertEqual(norm.financials.normalized_subtotal, Decimal('1200.00'))
        self.assertEqual(norm.financials.normalized_discount, Decimal('50.00'))
        self.assertEqual(norm.financials.normalized_tax, Decimal('120.00'))

    def test_multi_currency_conversion_with_explicit_rate(self):
        """INR quotation normalized to target USD using explicit documented exchange rate."""
        extracted = {
            'supplier': {'supplier_name': 'Bharat Steel Works'},
            'quotation': {
                'currency': 'INR',
                'subtotal': 100000.0,  # ₹100,000 INR
                'tax': 18000.0,        # 18% GST (₹18,000 INR)
                'grand_total': 118000.0,
            },
            'line_items': [
                {
                    'line_number': 1,
                    'description': 'Structural Steel Beam',
                    'quantity': 1000,
                    'unit': 'KG',
                    'unit_price': 100.0,  # ₹100 / KG
                    'discount': 0.0,
                    'tax': 0.0,
                    'total': 100000.0,
                }
            ],
        }

        norm = self.service.normalize(extracted_data=extracted, target_currency='USD')

        self.assertEqual(norm.financials.native_currency, 'INR')
        self.assertEqual(norm.financials.normalized_currency, 'USD')

        # 100,000 INR * 0.01156 = $1,156.00 USD
        self.assertEqual(norm.financials.normalized_subtotal, Decimal('1156.00'))
        self.assertIsNotNone(norm.financials.currency_conversion)
        self.assertEqual(norm.financials.currency_conversion.rate_source, 'RBI Fixing Benchmark')

        # Line item price: ₹100.00 * 0.01156 = $1.16 USD / KG
        self.assertEqual(norm.items[0].normalized_unit_price, Decimal('1.16'))

    def test_missing_exchange_rate_never_invented(self):
        """When currency conversion is requested but no rate exists, retains native currency and logs warning."""
        extracted = {
            'supplier': {'supplier_name': 'Tokyo Precision'},
            'quotation': {
                'currency': 'JPY',
                'subtotal': 500000.0,
            },
            'line_items': [],
        }

        # No JPY->USD rate exists in setup table
        norm = self.service.normalize(extracted_data=extracted, target_currency='USD')

        # Must NOT invent a rate; must retain JPY and add warning
        self.assertEqual(norm.financials.normalized_currency, 'JPY')
        self.assertTrue(any('No explicit exchange rate found' in w for w in norm.warnings))
        self.assertTrue(any('Exchange rates are never invented' in w for w in norm.warnings))
