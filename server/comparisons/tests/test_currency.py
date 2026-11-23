"""
Unit tests for Currency Normalization and Explicit Currency Conversion.
Verifies that:
- Currencies and symbols (INR vs USD vs EUR) are cleanly recognized.
- Exchange rates are NEVER invented or guessed.
- Currency conversions require explicit rates with documented source and date.
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase

from comparisons.normalization.currency import (
    CurrencyConversionService,
    ExchangeRate,
    ExchangeRateTable,
    MissingExchangeRateError,
    normalize_currency_code,
)


class CurrencyNormalizationTestCase(TestCase):
    def test_currency_code_normalization(self):
        """INR, USD, EUR, GBP symbol and string normalization."""
        self.assertEqual(normalize_currency_code('INR'), 'INR')
        self.assertEqual(normalize_currency_code('₹'), 'INR')
        self.assertEqual(normalize_currency_code('Rs'), 'INR')
        self.assertEqual(normalize_currency_code('Rs.'), 'INR')
        self.assertEqual(normalize_currency_code('inr ₹'), 'INR')

        self.assertEqual(normalize_currency_code('USD'), 'USD')
        self.assertEqual(normalize_currency_code('$'), 'USD')
        self.assertEqual(normalize_currency_code('us$'), 'USD')

        self.assertEqual(normalize_currency_code('EUR'), 'EUR')
        self.assertEqual(normalize_currency_code('€'), 'EUR')

        self.assertEqual(normalize_currency_code('GBP'), 'GBP')
        self.assertEqual(normalize_currency_code('£'), 'GBP')

    def test_do_not_invent_exchange_rates(self):
        """Converting between different currencies without explicit rate must raise MissingExchangeRateError."""
        empty_table = ExchangeRateTable()
        service = CurrencyConversionService(empty_table)

        with self.assertRaises(MissingExchangeRateError) as ctx:
            service.convert(
                amount=Decimal('1000.00'),
                source_currency='EUR',
                target_currency='USD',
            )

        self.assertIn("No explicit exchange rate found", str(ctx.exception))
        self.assertIn("Exchange rates must never be invented", str(ctx.exception))

    def test_explicit_currency_conversion_with_source_and_date(self):
        """Currency conversion succeeds when explicit rate with source and date is provided."""
        rate_table = ExchangeRateTable([
            ExchangeRate(
                source_currency='EUR',
                target_currency='USD',
                rate=Decimal('1.0850'),
                rate_source='European Central Bank (ECB Fixing)',
                rate_date=date(2026, 11, 20),
            ),
            ExchangeRate(
                source_currency='USD',
                target_currency='INR',
                rate=Decimal('86.50'),
                rate_source='Reserve Bank of India (RBI Reference)',
                rate_date=date(2026, 11, 20),
            ),
        ])
        service = CurrencyConversionService(rate_table)

        # 1. EUR to USD
        res1 = service.convert(Decimal('100.00'), 'EUR', 'USD')
        self.assertEqual(res1.converted_amount, Decimal('108.50'))
        self.assertEqual(res1.rate_source, 'European Central Bank (ECB Fixing)')
        self.assertEqual(res1.rate_date, date(2026, 11, 20))
        self.assertEqual(res1.exchange_rate, Decimal('1.0850'))

        # 2. USD to INR (e.g. $10.00 -> ₹865.00)
        res2 = service.convert(Decimal('10.00'), 'USD', 'INR')
        self.assertEqual(res2.converted_amount, Decimal('865.00'))
        self.assertEqual(res2.target_currency, 'INR')
        self.assertEqual(res2.rate_source, 'Reserve Bank of India (RBI Reference)')

    def test_identity_conversion_same_currency(self):
        """Same currency requires no external rate."""
        service = CurrencyConversionService(ExchangeRateTable())
        res = service.convert(Decimal('250.75'), 'USD', 'USD')
        self.assertEqual(res.converted_amount, Decimal('250.75'))
        self.assertTrue(res.is_identity)
        self.assertEqual(res.exchange_rate, Decimal('1.0'))

    def test_derived_inverse_exchange_rate(self):
        """When A->B is provided, B->A can be derived as 1/rate with provenance."""
        rate_table = ExchangeRateTable([
            ExchangeRate(
                source_currency='USD',
                target_currency='INR',
                rate=Decimal('80.0'),
                rate_source='RBI Benchmark',
                rate_date=date(2026, 11, 20),
            )
        ])
        service = CurrencyConversionService(rate_table)

        # INR to USD inverse: 800 INR / 80.0 = $10.00 USD
        res = service.convert(Decimal('800.00'), 'INR', 'USD')
        self.assertEqual(res.converted_amount, Decimal('10.00'))
        self.assertIn("Derived Inverse", res.rate_source)
