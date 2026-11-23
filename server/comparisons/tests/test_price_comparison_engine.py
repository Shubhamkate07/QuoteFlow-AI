"""
Comprehensive unit tests for the Deterministic Price Comparison Engine in QuoteFlow AI.
Tests calculation formulas, line-item comparisons, grand totals, multi-currency handling,
quantity scaling, incompatible item exclusion, mathematical inconsistency detection,
cherry-pick savings, and API endpoints.
"""
from datetime import date
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from comparisons.engine import (
    CalculationInconsistency,
    InconsistencySeverity,
    ItemCompatibilityStatus,
    PriceComparisonEngine,
    assign_ranks,
    calculate_extended_price,
    calculate_grand_total,
    calculate_percentage_difference,
    calculate_price_difference,
    calculate_savings_amount,
    calculate_savings_percentage,
    calculate_scaled_target_price,
    calculate_subtotal,
    quantize_currency,
    quantize_percentage,
    quantize_unit_price,
    to_decimal,
)
from comparisons.engine.validator import ComparisonValidator, ComparisonValidationError
from comparisons.models import ExchangeRate, RFQComparisonSnapshot
from comparisons.normalization import ExchangeRate as DomainExchangeRate, ExchangeRateTable
from organizations.models import Organization, OrganizationMembership
from quotations.models import Quotation, QuotationItem, QuotationStatus
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier

User = get_user_model()


class PriceComparisonFormulasTests(TestCase):
    """Unit tests for deterministic mathematical formulas and precision."""

    def test_to_decimal_robustness(self):
        self.assertEqual(to_decimal(10), Decimal('10.00'))
        self.assertEqual(to_decimal('125.50'), Decimal('125.50'))
        self.assertEqual(to_decimal('$1,250.75'), Decimal('1250.75'))
        self.assertEqual(to_decimal(None, default='0.00'), Decimal('0.00'))
        self.assertEqual(to_decimal('', default='5.00'), Decimal('5.00'))

    def test_calculate_extended_price(self):
        # Qty 10 @ $25.00, Disc $10.00, Tax $5.00 => 250 - 10 + 5 = 245.00
        total = calculate_extended_price(
            quantity='10',
            unit_price='25.00',
            discount='10.00',
            tax='5.00',
        )
        self.assertEqual(total, Decimal('245.00'))

    def test_calculate_extended_price_missing_values(self):
        # Missing discount and tax default to 0.00
        total = calculate_extended_price(quantity=5, unit_price='12.50', discount=None, tax=None)
        self.assertEqual(total, Decimal('62.50'))

    def test_calculate_subtotal(self):
        items = [Decimal('120.00'), Decimal('350.50'), Decimal('29.50')]
        self.assertEqual(calculate_subtotal(items), Decimal('500.00'))
        self.assertEqual(calculate_subtotal([]), Decimal('0.00'))

    def test_calculate_grand_total(self):
        # Subtotal $1,000, Disc $50, Tax $80, Shipping $120 => 1000 - 50 + 80 + 120 = 1150.00
        gt = calculate_grand_total(
            subtotal='1000.00',
            discount='50.00',
            tax='80.00',
            shipping='120.00',
        )
        self.assertEqual(gt, Decimal('1150.00'))

    def test_calculate_grand_total_missing_shipping_and_tax(self):
        # When shipping and tax are omitted, they safely default to 0.00
        gt = calculate_grand_total(subtotal='500.00', discount=None, tax=None, shipping=None)
        self.assertEqual(gt, Decimal('500.00'))

    def test_calculate_price_difference(self):
        # Higher price: $150 vs $100 => +$50
        self.assertEqual(calculate_price_difference('150.00', '100.00'), Decimal('50.00'))
        # Equal price => $0.00
        self.assertEqual(calculate_price_difference('100.00', '100.00'), Decimal('0.00'))
        # Lower price: $80 vs $100 => -$20
        self.assertEqual(calculate_price_difference('80.00', '100.00'), Decimal('-20.00'))

    def test_calculate_percentage_difference(self):
        # $150 vs $100 baseline => +50.00%
        self.assertEqual(calculate_percentage_difference('150.00', '100.00'), Decimal('50.00'))
        # Equal => 0.00%
        self.assertEqual(calculate_percentage_difference('100.00', '100.00'), Decimal('0.00'))
        # Baseline is 0 => safely returns 0.00% without ZeroDivisionError
        self.assertEqual(calculate_percentage_difference('100.00', '0.00'), Decimal('0.00'))

    def test_calculate_scaled_target_price(self):
        # Target RFQ Qty 100, Normalized Unit Price $15.25 => $1,525.00
        scaled = calculate_scaled_target_price('100', '15.25')
        self.assertEqual(scaled, Decimal('1525.00'))

    def test_calculate_savings_amount_and_percentage(self):
        # Baseline $1,000, Best $800 => Savings $200 (20.00%)
        amount = calculate_savings_amount('1000.00', '800.00')
        pct = calculate_savings_percentage('1000.00', '800.00')
        self.assertEqual(amount, Decimal('200.00'))
        self.assertEqual(pct, Decimal('20.00'))

        # When baseline is lower than best, savings is 0
        self.assertEqual(calculate_savings_amount('500.00', '600.00'), Decimal('0.00'))
        self.assertEqual(calculate_savings_percentage('500.00', '600.00'), Decimal('0.00'))

    def test_assign_ranks_with_ties(self):
        # Prices: [100, 150, 150, 200]
        data = [
            {'name': 'A', 'price': Decimal('150.00')},
            {'name': 'B', 'price': Decimal('100.00')},
            {'name': 'C', 'price': Decimal('200.00')},
            {'name': 'D', 'price': Decimal('150.00')},
        ]
        ranked = assign_ranks(data, key_func=lambda x: x['price'])
        # Expect B: Rank 1 ($100), A & D: Rank 2 ($150), C: Rank 4 ($200)
        rank_map = {item['name']: rank for rank, item in ranked}
        self.assertEqual(rank_map['B'], 1)
        self.assertEqual(rank_map['A'], 2)
        self.assertEqual(rank_map['D'], 2)
        self.assertEqual(rank_map['C'], 4)


class PriceComparisonEngineIntegrationTests(TestCase):
    """End-to-end integration tests for PriceComparisonEngine with database models."""

    def setUp(self):
        self.org = Organization.objects.create(name="Acme Corp", slug="acme-corp")
        self.user = User.objects.create_user(
            username="analyst@acme.com",
            email="analyst@acme.com",
            password="testpassword123",
            first_name="Jane",
            last_name="Doe",
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role='manager',
        )

        # Suppliers
        self.sup1 = Supplier.objects.create(
            organization=self.org,
            company_name="Alpha Industrial",
            email="contact@alpha.com",
            country="US",
        )
        self.sup2 = Supplier.objects.create(
            organization=self.org,
            company_name="Beta Manufacturing",
            email="sales@beta.com",
            country="US",
        )
        self.sup3 = Supplier.objects.create(
            organization=self.org,
            company_name="Gamma Global",
            email="info@gamma.de",
            country="DE",
        )

        # RFQ with 2 Items
        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number="RFQ-2026-001",
            title="CNC Machined Components",
            currency="USD",
            status=RFQStatus.OPEN,
            created_by=self.user,
        )
        self.rfq_item1 = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Precision Shaft",
            description="Steel CNC Shaft 50mm",
            quantity=Decimal('100.00'),
            unit="EA",
            target_unit_price=Decimal('50.00'),
        )
        self.rfq_item2 = RFQItem.objects.create(
            rfq=self.rfq,
            position=2,
            item_name="Alloy Bushing",
            description="Bronze Bushing 20mm",
            quantity=Decimal('50.00'),
            unit="EA",
            target_unit_price=Decimal('20.00'),
        )

        # Quotation 1 (Alpha): Shaft @ $45.00, Bushing @ $18.00, Shipping $100
        # Subtotal: (100 * 45) + (50 * 18) = 4500 + 900 = 5400. Grand Total: 5400 + 100 = 5500 USD
        self.q1 = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup1,
            quotation_number="QT-ALPHA-101",
            currency="USD",
            quotation_date=date(2026, 11, 20),
            subtotal=Decimal('5400.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('5500.00'),
            lead_time_weeks=3,
            delivery_terms="DAP Chicago",
            payment_terms="Net 30 Days",
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=self.q1,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('100.00'),
            unit="EA",
            unit_price=Decimal('45.00'),
            line_total=Decimal('4500.00'),
        )
        QuotationItem.objects.create(
            quotation=self.q1,
            rfq_item=self.rfq_item2,
            position=2,
            description="Alloy Bushing",
            quantity=Decimal('50.00'),
            unit="EA",
            unit_price=Decimal('18.00'),
            line_total=Decimal('900.00'),
        )

        # Quotation 2 (Beta): Shaft @ $42.00, Bushing @ $22.00, Shipping $50
        # Subtotal: (100 * 42) + (50 * 22) = 4200 + 1100 = 5300. Grand Total: 5300 + 50 = 5350 USD
        self.q2 = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup2,
            quotation_number="QT-BETA-202",
            currency="USD",
            quotation_date=date(2026, 11, 20),
            subtotal=Decimal('5300.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('5350.00'),
            lead_time_weeks=2,
            delivery_terms="FOB Origin",
            payment_terms="Net 45 Days",
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=self.q2,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('100.00'),
            unit="EA",
            unit_price=Decimal('42.00'),
            line_total=Decimal('4200.00'),
        )
        QuotationItem.objects.create(
            quotation=self.q2,
            rfq_item=self.rfq_item2,
            position=2,
            description="Alloy Bushing",
            quantity=Decimal('50.00'),
            unit="EA",
            unit_price=Decimal('22.00'),
            line_total=Decimal('1100.00'),
        )

    def test_apples_to_apples_price_comparison(self):
        """Verifies unit prices, extended prices, lowest price detection, and rankings."""
        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[self.q1, self.q2],
            comparison_currency="USD",
        )
        summary = engine.compare()

        self.assertEqual(summary.quotations_compared_count, 2)
        self.assertEqual(summary.comparison_currency, "USD")

        # Line Item 1 (Shaft): Beta ($42.00) is lowest, Alpha ($45.00) is +$3.00 (+7.14%)
        item1_res = next(it for it in summary.items_matrix if it.rfq_item_id == str(self.rfq_item1.id))
        self.assertEqual(item1_res.lowest_unit_price, Decimal('42.00'))
        self.assertEqual(item1_res.lowest_extended_price, Decimal('4200.00'))
        self.assertEqual(item1_res.lowest_bidder_id, str(self.sup2.id))

        beta_bid_1 = item1_res.bids[str(self.sup2.id)]
        self.assertTrue(beta_bid_1.is_lowest_extended_price)
        self.assertEqual(beta_bid_1.item_rank, 1)
        self.assertEqual(beta_bid_1.price_difference, Decimal('0.00'))
        self.assertEqual(beta_bid_1.percentage_difference, Decimal('0.00'))

        alpha_bid_1 = item1_res.bids[str(self.sup1.id)]
        self.assertFalse(alpha_bid_1.is_lowest_extended_price)
        self.assertEqual(alpha_bid_1.item_rank, 2)
        self.assertEqual(alpha_bid_1.price_difference, Decimal('300.00'))
        self.assertEqual(alpha_bid_1.percentage_difference, Decimal('7.14'))

        # Line Item 2 (Bushing): Alpha ($18.00) is lowest, Beta ($22.00) is +$4.00 (+22.22%)
        item2_res = next(it for it in summary.items_matrix if it.rfq_item_id == str(self.rfq_item2.id))
        self.assertEqual(item2_res.lowest_unit_price, Decimal('18.00'))
        self.assertEqual(item2_res.lowest_extended_price, Decimal('900.00'))
        self.assertEqual(item2_res.lowest_bidder_id, str(self.sup1.id))

        # Overall Quotation Totals:
        # Beta Grand Total is $5,350.00 (Rank 1)
        # Alpha Grand Total is $5,500.00 (Rank 2)
        # Difference = $150.00 (+2.80%)
        self.assertEqual(summary.lowest_grand_total, Decimal('5350.00'))
        self.assertEqual(summary.lowest_supplier_name, "Beta Manufacturing")
        self.assertEqual(summary.highest_grand_total, Decimal('5500.00'))
        self.assertEqual(summary.max_savings_amount, Decimal('150.00'))
        self.assertEqual(summary.max_savings_percentage, Decimal('2.73'))

        q_beta = next(q for q in summary.quotations if q.quotation_id == str(self.q2.id))
        self.assertEqual(q_beta.rank, 1)
        self.assertTrue(q_beta.is_lowest_grand_total)

        q_alpha = next(q for q in summary.quotations if q.quotation_id == str(self.q1.id))
        self.assertEqual(q_alpha.rank, 2)
        self.assertEqual(q_alpha.price_difference_vs_lowest, Decimal('150.00'))
        self.assertEqual(q_alpha.percentage_difference_vs_lowest, Decimal('2.80'))

    def test_cherry_pick_split_award_savings(self):
        """
        Cherry-pick analysis:
        Item 1 lowest is Beta @ $4,200.00
        Item 2 lowest is Alpha @ $900.00
        Cherry-pick total = $4,200 + $900 = $5,100.00
        Lowest single vendor is Beta @ $5,350.00 (with $50 shipping)
        Split-award savings = $5,350 - $5,100 = $250.00
        """
        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[self.q1, self.q2],
            comparison_currency="USD",
        )
        summary = engine.compare()

        self.assertEqual(summary.cherry_pick_total, Decimal('5100.00'))
        self.assertEqual(summary.cherry_pick_savings, Decimal('250.00'))
        self.assertEqual(summary.cherry_pick_savings_percentage, Decimal('4.67'))

    def test_multi_currency_comparison_with_exchange_rates(self):
        """
        Tests multi-currency quotation:
        Gamma quotes in EUR.
        Exchange rate: 1 EUR = 1.10 USD (Official ECB rate).
        Shaft @ 35.00 EUR => 38.50 USD
        Bushing @ 15.00 EUR => 16.50 USD
        """
        rate_table = ExchangeRateTable()
        rate_table.add_rate(
            DomainExchangeRate(
                source_currency="EUR",
                target_currency="USD",
                rate=Decimal('1.10000000'),
                rate_source="European Central Bank",
                rate_date=date(2026, 11, 20),
            )
        )

        q3 = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup3,
            quotation_number="QT-GAMMA-303",
            currency="EUR",
            quotation_date=date(2026, 11, 20),
            subtotal=Decimal('4250.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('4350.00'), # 100 EUR shipping
            lead_time_weeks=4,
            delivery_terms="CIF New York",
            payment_terms="Net 30 Days",
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=q3,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('100.00'),
            unit="EA",
            unit_price=Decimal('35.00'), # 35 * 1.10 = 38.50 USD
            line_total=Decimal('3500.00'),
        )
        QuotationItem.objects.create(
            quotation=q3,
            rfq_item=self.rfq_item2,
            position=2,
            description="Alloy Bushing",
            quantity=Decimal('50.00'),
            unit="EA",
            unit_price=Decimal('15.00'), # 15 * 1.10 = 16.50 USD
            line_total=Decimal('750.00'),
        )

        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[self.q1, self.q2, q3],
            comparison_currency="USD",
            exchange_rate_table=rate_table,
        )
        summary = engine.compare()

        self.assertEqual(summary.quotations_compared_count, 3)

        # Gamma Shaft is 38.50 USD => New Lowest! (beats Beta's 42.00)
        item1_res = next(it for it in summary.items_matrix if it.rfq_item_id == str(self.rfq_item1.id))
        self.assertEqual(item1_res.lowest_unit_price, Decimal('38.50'))
        self.assertEqual(item1_res.lowest_bidder_id, str(self.sup3.id))

        # Check Gamma quotation record has exchange rate citation
        gamma_q = next(q for q in summary.quotations if q.quotation_id == str(q3.id))
        self.assertEqual(gamma_q.native_currency, "EUR")
        self.assertEqual(gamma_q.comparison_currency, "USD")
        self.assertEqual(gamma_q.exchange_rate_applied, Decimal('1.10000000'))
        self.assertEqual(gamma_q.rate_source, "European Central Bank")

    def test_missing_exchange_rate_fails_gracefully(self):
        """
        When a quote uses a foreign currency with NO exchange rate defined,
        it must be marked as incomparable without inventing rates or crashing.
        """
        q_foreign = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup3,
            quotation_number="QT-JPY-404",
            currency="JPY",
            quotation_date=date(2026, 11, 20),
            subtotal=Decimal('500000.00'),
            total_amount=Decimal('500000.00'),
            created_by=self.user,
        )
        # Empty rate table (no JPY -> USD rate)
        empty_table = ExchangeRateTable()

        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[self.q1, q_foreign],
            comparison_currency="USD",
            exchange_rate_table=empty_table,
        )
        summary = engine.compare()

        jpy_q = next(q for q in summary.quotations if q.quotation_id == str(q_foreign.id))
        self.assertFalse(jpy_q.is_comparable)
        self.assertTrue(any("cannot be converted to USD" in w for w in summary.warnings))

    def test_quantity_scaling_consistency(self):
        """
        RFQ requests 100 EA.
        Supplier quotes 50 EA @ $10.00 each.
        Extended quoted qty = 50 * 10 = $500.00.
        Extended target qty = 100 * 10 = $1,000.00.
        Comparison engine evaluates both and scales target qty for apples-to-apples fairness.
        """
        q_partial = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup1,
            quotation_number="QT-PARTIAL-505",
            currency="USD",
            quotation_date=date(2026, 11, 20),
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=q_partial,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('50.00'), # Quoted 50 instead of 100
            unit="EA",
            unit_price=Decimal('10.00'),
            line_total=Decimal('500.00'),
        )

        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[q_partial],
            comparison_currency="USD",
        )
        summary = engine.compare()

        item1_res = summary.items_matrix[0]
        bid = item1_res.bids[str(self.sup1.id)]
        self.assertEqual(bid.quoted_quantity, Decimal('50.00'))
        self.assertEqual(bid.extended_price_quoted_qty, Decimal('500.00'))
        self.assertEqual(bid.extended_price_target_qty, Decimal('1000.00'))

    def test_incompatible_item_exclusion(self):
        """
        When an item has incompatible UoM (e.g. quoted in meters for an EA count RFQ),
        it must be flagged as INCOMPATIBLE and excluded from lowest comparable price.
        """
        q_incompat = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup2,
            quotation_number="QT-INCOMPAT-606",
            currency="USD",
            created_by=self.user,
        )
        item_incompat = QuotationItem.objects.create(
            quotation=q_incompat,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('10.00'),
            unit="METERS", # Incompatible with EA
            unit_price=Decimal('1.00'), # Extremely cheap, but incompatible
            match_type='incompatible',
            line_total=Decimal('10.00'),
        )

        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[self.q1, q_incompat],
            comparison_currency="USD",
        )
        summary = engine.compare()

        item1_res = summary.items_matrix[0]
        incompat_bid = item1_res.bids[str(self.sup2.id)]
        self.assertEqual(incompat_bid.compatibility_status, ItemCompatibilityStatus.INCOMPATIBLE)
        # Lowest price must NOT be $1.00; must be Alpha's valid $45.00 quote
        self.assertEqual(item1_res.lowest_unit_price, Decimal('45.00'))

    def test_calculation_inconsistency_detection(self):
        """
        If a vendor's document states:
        Item: 10 @ $20 = $250 (stated) instead of $200 (calculated)
        The engine must record an inconsistency flag with variance +$50.00.
        """
        q_err = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup1,
            quotation_number="QT-MATH-ERR-707",
            currency="USD",
            subtotal=Decimal('250.00'),
            total_amount=Decimal('250.00'),
            created_by=self.user,
        )
        QuotationItem.objects.create(
            quotation=q_err,
            rfq_item=self.rfq_item1,
            position=1,
            description="Precision Shaft",
            quantity=Decimal('10.00'),
            unit="EA",
            unit_price=Decimal('20.00'),
            line_total=Decimal('250.00'), # 10 * 20 is 200, but printed 250
        )

        engine = PriceComparisonEngine(
            rfq=self.rfq,
            quotations=[q_err],
            comparison_currency="USD",
        )
        summary = engine.compare()

        item1_bid = summary.items_matrix[0].bids[str(self.sup1.id)]
        self.assertTrue(item1_bid.has_calculation_inconsistency)
        self.assertEqual(len(item1_bid.inconsistencies), 1)
        inc = item1_bid.inconsistencies[0]
        self.assertEqual(inc.variance, Decimal('50.00'))
        self.assertEqual(inc.severity, InconsistencySeverity.ERROR)


class ComparisonAPITests(APITestCase):
    """Integration tests for comparison REST API endpoints and tenant isolation."""

    def setUp(self):
        self.org1 = Organization.objects.create(name="Org One", slug="org-one")
        self.org2 = Organization.objects.create(name="Org Two", slug="org-two")

        self.user1 = User.objects.create_user(
            username="user1@org1.com",
            email="user1@org1.com",
            password="testpassword123",
        )
        OrganizationMembership.objects.create(
            user=self.user1,
            organization=self.org1,
            role='manager',
        )

        self.user2 = User.objects.create_user(
            username="user2@org2.com",
            email="user2@org2.com",
            password="testpassword123",
        )
        OrganizationMembership.objects.create(
            user=self.user2,
            organization=self.org2,
            role='manager',
        )

        self.supplier = Supplier.objects.create(
            organization=self.org1,
            company_name="Apex Supplier",
            email="apex@supplier.com",
            country="US",
        )

        self.rfq = RFQ.objects.create(
            organization=self.org1,
            rfq_number="RFQ-API-001",
            title="Fasteners Package",
            currency="USD",
            created_by=self.user1,
        )
        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="M8 Bolt",
            description="Grade 8.8 Hex Bolt",
            quantity=Decimal('500.00'),
            unit="EA",
        )

        self.quote = Quotation.objects.create(
            organization=self.org1,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number="QT-APEX-001",
            currency="USD",
            subtotal=Decimal('250.00'),
            total_amount=Decimal('250.00'),
            created_by=self.user1,
        )
        QuotationItem.objects.create(
            quotation=self.quote,
            rfq_item=self.rfq_item,
            position=1,
            description="M8 Bolt",
            quantity=Decimal('500.00'),
            unit="EA",
            unit_price=Decimal('0.50'),
            line_total=Decimal('250.00'),
        )

    def test_get_rfq_comparison_endpoint(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"/api/comparisons/rfqs/{self.rfq.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org1.id),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['rfq_id'], str(self.rfq.id))
        self.assertEqual(data['quotations_compared_count'], 1)
        self.assertEqual(data['lowest_grand_total'], 250.0)
        self.assertEqual(len(data['items_matrix']), 1)
        self.assertEqual(len(data['quotations']), 1)

        # Verify comparison snapshot was persisted
        self.assertEqual(RFQComparisonSnapshot.objects.filter(rfq=self.rfq).count(), 1)

    def test_post_rfq_compare_endpoint_with_custom_currency(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            f"/api/comparisons/rfqs/{self.rfq.id}/compare/",
            data={'comparison_currency': 'USD', 'save_snapshot': True},
            format='json',
            HTTP_X_ORGANIZATION_ID=str(self.org1.id),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comparison_currency'], 'USD')

    def test_cross_tenant_isolation_blocked(self):
        """User from Org 2 cannot compare or access Org 1 RFQ."""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(
            f"/api/comparisons/rfqs/{self.rfq.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org2.id),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comparison_history_endpoint(self):
        self.client.force_authenticate(user=self.user1)
        # Create a comparison run first
        self.client.get(
            f"/api/comparisons/rfqs/{self.rfq.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org1.id),
        )
        # Get history
        hist_response = self.client.get(
            f"/api/comparisons/rfqs/{self.rfq.id}/history/",
            HTTP_X_ORGANIZATION_ID=str(self.org1.id),
        )
        self.assertEqual(hist_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(hist_response.data), 1)
