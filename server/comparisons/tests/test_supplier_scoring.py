"""
Unit and Integration Tests for Explainable Supplier Scoring Engine in QuoteFlow AI.

Covers:
1. Strict weight validation (sum must equal 100%, non-negative, decimal scaling)
2. Individual factor scores and transparent formula explanations
3. Final score aggregation and rankings
4. Proof of weight sensitivity: altering weights changes winner between Cheap/Slow vs Premium/Fast vendor
5. Critical specification mismatch penalization
6. Decision support disclaimer and no-auto-purchase guardrail
7. Django model integration and REST API endpoints (GET/POST /api/comparisons/rfqs/{id}/scoring/)
8. Multi-tenant security isolation
"""
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from comparisons.scoring import (
    SCORING_SYSTEM_LIMITATIONS,
    ScoringFactor,
    ScoringWeights,
    SupplierScoringEngine,
    WeightValidationError,
    validate_weights,
)
from organizations.models import Organization, OrganizationMembership
from quotations.models import Quotation, QuotationItem
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier

User = get_user_model()


class ScoringWeightsValidationTests(TestCase):
    """Tests strictly enforcing weight validation and constraints."""

    def test_default_weights_valid(self):
        """Default weights: 40% price, 30% spec, 15% delivery, 10% payment, 5% warranty = 100%."""
        weights = ScoringWeights()
        self.assertEqual(weights.price + weights.spec_match + weights.delivery + weights.payment_terms + weights.warranty, 100.0)
        validated = validate_weights(weights)
        self.assertEqual(validated.price, 40.0)

    def test_custom_valid_percentage_weights(self):
        """Valid custom weights summing to 100%."""
        custom = {'price': 50.0, 'spec_match': 20.0, 'delivery': 10.0, 'payment_terms': 10.0, 'warranty': 10.0}
        validated = validate_weights(custom)
        self.assertEqual(validated.price, 50.0)
        self.assertEqual(validated.warranty, 10.0)

    def test_decimal_fraction_auto_scaling(self):
        """Decimal fractions summing to 1.0 (e.g. 0.40, 0.30, 0.15, 0.10, 0.05) are auto-scaled to 100%."""
        decimals = {'price': 0.40, 'spec_match': 0.30, 'delivery': 0.15, 'payment_terms': 0.10, 'warranty': 0.05}
        validated = validate_weights(decimals)
        self.assertEqual(validated.price, 40.0)
        self.assertEqual(validated.spec_match, 30.0)
        self.assertEqual(validated.delivery, 15.0)

    def test_weights_sum_less_than_100_rejected(self):
        """Sum = 95% raises WeightValidationError."""
        invalid = {'price': 40.0, 'spec_match': 30.0, 'delivery': 10.0, 'payment_terms': 10.0, 'warranty': 5.0}
        with self.assertRaises(WeightValidationError) as ctx:
            validate_weights(invalid)
        self.assertIn("must total exactly 100%", str(ctx.exception))
        self.assertIn("95.00%", str(ctx.exception))

    def test_weights_sum_greater_than_100_rejected(self):
        """Sum = 110% raises WeightValidationError."""
        invalid = {'price': 50.0, 'spec_match': 30.0, 'delivery': 15.0, 'payment_terms': 10.0, 'warranty': 5.0}
        with self.assertRaises(WeightValidationError) as ctx:
            validate_weights(invalid)
        self.assertIn("must total exactly 100%", str(ctx.exception))
        self.assertIn("110.00%", str(ctx.exception))

    def test_negative_weight_rejected(self):
        """Negative weight raises WeightValidationError."""
        invalid = {'price': 60.0, 'spec_match': 30.0, 'delivery': -5.0, 'payment_terms': 10.0, 'warranty': 5.0}
        with self.assertRaises(WeightValidationError) as ctx:
            validate_weights(invalid)
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_unknown_factor_rejected(self):
        """Unknown factor key raises WeightValidationError."""
        invalid = {'price': 40.0, 'spec_match': 30.0, 'delivery': 15.0, 'payment_terms': 10.0, 'esg_score': 5.0}
        with self.assertRaises(WeightValidationError) as ctx:
            validate_weights(invalid)
        self.assertIn("Unknown scoring factor", str(ctx.exception))


class ExplainableScoringEngineLogicTests(TestCase):
    """Validates explainability, formulas, and sensitivity to weight adjustments."""

    def setUp(self):
        self.engine = SupplierScoringEngine()
        self.today = date(2026, 11, 22)

    def test_individual_factor_explainability_and_formulas(self):
        """Verifies every factor outputs transparent formulas, raw metrics, and plain English explanations."""
        rfq_data = {
            'rfq_number': 'RFQ-TEST-001',
            'currency': 'USD',
            'required_delivery_date': '2026-12-01',
            'items': [
                {
                    'id': 'rfq-it-1',
                    'position': 1,
                    'item_name': 'Hydraulic Pump',
                    'quantity': '1',
                    'custom_specifications': {'Pressure': '250 bar', 'Voltage': '24V DC'},
                }
            ],
        }

        quote_data = {
            'id': 'quote-1',
            'quotation_number': 'Q-PUMP-99',
            'supplier_name': 'HydroTech Corp',
            'financials': {'normalized_grand_total': Decimal('1250.00'), 'currency': 'USD'},
            'commercial': {
                'delivery_date': date(2026, 12, 1),  # On-time
                'payment_terms': 'Net 30 days',
                'warranty_information': '24 months manufacturer warranty',
            },
            'items': [
                {
                    'rfq_item_id': 'rfq-it-1',
                    'position': 1,
                    'description': 'Hydraulic Pump 250bar',
                    'specifications': {'Pressure': '250 bar', 'Voltage': '24V DC'},
                }
            ],
        }

        # Suppose benchmark lowest price across RFQ is $1,000.00
        summary = self.engine.score_rfq_quotations(
            rfq_or_data=rfq_data,
            quotations_or_data=[quote_data],
            evaluation_date=self.today,
        )

        self.assertEqual(len(summary.rankings), 1)
        report = summary.rankings[0]

        # 1. Price Factor: (1250.00 / 1250.00) * 100 = 100 (since it is sole quote)
        price_factor = report.factors[ScoringFactor.PRICE.value]
        self.assertEqual(price_factor.normalized_score, 100.0)
        self.assertEqual(price_factor.weight_pct, 40.0)
        self.assertEqual(price_factor.weighted_score, 40.0)
        self.assertIn("100.00", price_factor.formula_applied)
        self.assertIn("HydroTech Corp", report.supplier_name)

        # 2. Spec Factor: 100% match
        spec_factor = report.factors[ScoringFactor.SPEC_MATCH.value]
        self.assertEqual(spec_factor.normalized_score, 100.0)
        self.assertEqual(spec_factor.weighted_score, 30.0)
        self.assertIn("100%", spec_factor.explanation)

        # 3. Delivery Factor: On-time -> 100
        deliv_factor = report.factors[ScoringFactor.DELIVERY.value]
        self.assertEqual(deliv_factor.normalized_score, 100.0)
        self.assertEqual(deliv_factor.weighted_score, 15.0)

        # 4. Payment Factor: Net 30 -> 85
        pay_factor = report.factors[ScoringFactor.PAYMENT_TERMS.value]
        self.assertEqual(pay_factor.normalized_score, 85.0)
        self.assertEqual(pay_factor.weighted_score, 8.5)

        # 5. Warranty Factor: 24 months -> 95
        war_factor = report.factors[ScoringFactor.WARRANTY.value]
        self.assertEqual(war_factor.normalized_score, 95.0)
        self.assertEqual(war_factor.weighted_score, 4.75)

        # Final score: 40 + 30 + 15 + 8.5 + 4.75 = 98.25
        self.assertEqual(report.final_score, 98.25)
        self.assertTrue(report.is_recommended_for_consideration)

    def test_weight_change_inverts_supplier_winner(self):
        """
        Proof of explainable weight sensitivity:
        Supplier A: Low Price ($1,000), but Slow Delivery (10 days late).
        Supplier B: Higher Price ($1,400), but Fast On-time Delivery (0 days delay) and Better Warranty.

        Under Price-Dominant Weights (60% Price, 10% Delivery): Supplier A wins Rank 1!
        Under Delivery-Dominant Weights (15% Price, 45% Delivery): Supplier B wins Rank 1!
        """
        rfq_data = {
            'rfq_number': 'RFQ-SENSITIVITY',
            'currency': 'USD',
            'required_delivery_date': date(2026, 12, 1),
            'items': [{'id': 'item-1', 'position': 1, 'item_name': 'CNC Machined Housing'}],
        }

        # Supplier A (Budget Vendor: Cheap but 10 days late)
        quote_a = {
            'id': 'quote-a',
            'quotation_number': 'Q-CHEAP-SLOW',
            'supplier_name': 'Budget Machining',
            'financials': {'normalized_grand_total': Decimal('1000.00'), 'currency': 'USD'},
            'commercial': {
                'delivery_date': date(2026, 12, 11),  # 10 days late
                'payment_terms': 'Net 30',
                'warranty_information': '12 months',
            },
            'items': [{'rfq_item_id': 'item-1', 'position': 1, 'specifications': {}}],
        }

        # Supplier B (Premium Vendor: 40% more expensive, but strictly on-time with 2-year warranty)
        quote_b = {
            'id': 'quote-b',
            'quotation_number': 'Q-PREMIUM-FAST',
            'supplier_name': 'Precision Speedworks',
            'financials': {'normalized_grand_total': Decimal('1400.00'), 'currency': 'USD'},
            'commercial': {
                'delivery_date': date(2026, 12, 1),   # On-time
                'payment_terms': 'Net 60',
                'warranty_information': '24 months',
            },
            'items': [{'rfq_item_id': 'item-1', 'position': 1, 'specifications': {}}],
        }

        quotes = [quote_a, quote_b]

        # ------------------------------------------------------------------
        # SCENARIO 1: Cost-Reduction Focus (Price 60%, Delivery 10%, Specs 20%, Payment 5%, Warranty 5%)
        # ------------------------------------------------------------------
        price_heavy_weights = ScoringWeights(
            price=60.0,
            delivery=10.0,
            spec_match=20.0,
            payment_terms=5.0,
            warranty=5.0,
        )
        summary_price_focus = self.engine.score_rfq_quotations(
            rfq_or_data=rfq_data,
            quotations_or_data=quotes,
            weights=price_heavy_weights,
            evaluation_date=self.today,
        )

        rank_1_price = summary_price_focus.rankings[0]
        rank_2_price = summary_price_focus.rankings[1]

        self.assertEqual(rank_1_price.supplier_name, 'Budget Machining')
        self.assertEqual(rank_2_price.supplier_name, 'Precision Speedworks')
        self.assertGreater(rank_1_price.final_score, rank_2_price.final_score)

        # ------------------------------------------------------------------
        # SCENARIO 2: Schedule & Assurance Focus (Delivery 45%, Price 15%, Specs 20%, Payment 10%, Warranty 10%)
        # ------------------------------------------------------------------
        delivery_heavy_weights = ScoringWeights(
            price=15.0,
            delivery=45.0,
            spec_match=20.0,
            payment_terms=10.0,
            warranty=10.0,
        )
        summary_delivery_focus = self.engine.score_rfq_quotations(
            rfq_or_data=rfq_data,
            quotations_or_data=quotes,
            weights=delivery_heavy_weights,
            evaluation_date=self.today,
        )

        rank_1_deliv = summary_delivery_focus.rankings[0]
        rank_2_deliv = summary_delivery_focus.rankings[1]

        # Winner inverts: Precision Speedworks is now Rank 1!
        self.assertEqual(rank_1_deliv.supplier_name, 'Precision Speedworks')
        self.assertEqual(rank_2_deliv.supplier_name, 'Budget Machining')
        self.assertGreater(rank_1_deliv.final_score, rank_2_deliv.final_score)

    def test_critical_spec_mismatch_overrides_to_zero(self):
        """A supplier with low price but critical spec mismatch (PNP vs NPN) gets 0 for specs."""
        rfq_data = {
            'rfq_number': 'RFQ-SPEC-CHECK',
            'items': [
                {
                    'id': 'rfq-item-1',
                    'position': 1,
                    'item_name': 'Optical Sensor',
                    'custom_specifications': {'Output': 'PNP'},
                }
            ],
        }

        quote_data = {
            'quotation_number': 'Q-CHEAP-WRONG-SPEC',
            'supplier_name': 'Incompatible Vendor',
            'financials': {'normalized_grand_total': Decimal('200.00'), 'currency': 'USD'},
            'commercial': {'payment_terms': 'Net 30', 'warranty_information': '12 months'},
            'items': [
                {
                    'rfq_item_id': 'rfq-item-1',
                    'position': 1,
                    'description': 'Optical Sensor NPN',
                    'specifications': {'Output': 'NPN'},  # Critical mismatch
                }
            ],
        }

        summary = self.engine.score_rfq_quotations(
            rfq_or_data=rfq_data,
            quotations_or_data=[quote_data],
        )

        rep = summary.rankings[0]
        spec_factor = rep.factors[ScoringFactor.SPEC_MATCH.value]
        self.assertEqual(spec_factor.normalized_score, 0.0)
        self.assertEqual(spec_factor.weighted_score, 0.0)
        self.assertIn("Critical Mismatches", spec_factor.formula_applied)
        self.assertFalse(rep.is_recommended_for_consideration)
        self.assertIn("Critical technical specification conflict", rep.advisory_notes[0])

    def test_disclaimer_and_documented_limitations_present(self):
        """Verifies clear disclaimers that system does not auto-purchase, and documents limitations."""
        summary = self.engine.score_rfq_quotations(
            rfq_or_data={'rfq_number': 'RFQ-TEST'},
            quotations_or_data=[],
        )
        self.assertIn("does NOT automatically select or purchase", summary.disclaimer)
        self.assertEqual(len(summary.scoring_limitations), len(SCORING_SYSTEM_LIMITATIONS))
        self.assertTrue(any("Linear Relative Price" in lim for lim in summary.scoring_limitations))


class DjangoModelAndAPIScoringTests(TestCase):
    """Integration tests with Django database models and DRF API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='procurement_lead@example.com',
            password='StrongPassword123!',
        )
        self.other_user = User.objects.create_user(
            email='external@othercorp.com',
            password='StrongPassword123!',
        )

        self.org = Organization.objects.create(name='Scoring Corp', slug='scoring-corp-org')
        self.other_org = Organization.objects.create(name='Rival Corp', slug='rival-scoring-org')

        OrganizationMembership.objects.create(user=self.user, organization=self.org, role='admin')
        OrganizationMembership.objects.create(user=self.other_user, organization=self.other_org, role='admin')

        self.sup1 = Supplier.objects.create(organization=self.org, company_name='Vendor Alpha', email='alpha@test.com')
        self.sup2 = Supplier.objects.create(organization=self.org, company_name='Vendor Beta', email='beta@test.com')

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-SCORE-2026',
            title='Subsea Valve Actuators',
            currency='USD',
            status=RFQStatus.OPEN,
            required_delivery_date=date(2026, 12, 15),
            created_by=self.user,
        )

        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name='Actuator Valve 4-inch',
            quantity=Decimal('10.0000'),
            unit='PCS',
            target_unit_price=Decimal('500.00'),
            custom_specifications={'Torque': '150 Nm', 'Voltage': '24V DC'},
        )

        # Quotation 1 (Alpha): Cheaper ($4,500), Net 30, 1-year warranty
        self.q1 = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup1,
            quotation_number='QUO-ALPHA-101',
            quotation_date=date(2026, 11, 20),
            currency='USD',
            payment_terms='Net 30 days',
            warranty_information='12 months standard warranty',
            subtotal=Decimal('4500.00'),
            total_amount=Decimal('4500.00'),
            status='received',
        )
        QuotationItem.objects.create(
            quotation=self.q1,
            rfq_item=self.rfq_item,
            position=1,
            description='Actuator Valve 4-inch 150Nm',
            quantity=Decimal('10.0000'),
            unit_price=Decimal('450.00'),
            line_total=Decimal('4500.00'),
            specifications={'Torque': '150 Nm', 'Voltage': '24V DC'},
        )

        # Quotation 2 (Beta): Slightly more ($5,000), Net 60, 2-year warranty
        self.q2 = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.sup2,
            quotation_number='QUO-BETA-202',
            quotation_date=date(2026, 11, 20),
            currency='USD',
            payment_terms='Net 60 days',
            warranty_information='24 months comprehensive warranty',
            subtotal=Decimal('5000.00'),
            total_amount=Decimal('5000.00'),
            status='received',
        )
        QuotationItem.objects.create(
            quotation=self.q2,
            rfq_item=self.rfq_item,
            position=1,
            description='Actuator Valve 4-inch Premium',
            quantity=Decimal('10.0000'),
            unit_price=Decimal('500.00'),
            line_total=Decimal('5000.00'),
            specifications={'Torque': '150 Nm', 'Voltage': '24V DC'},
        )

    def test_api_rfq_scoring_get_default_weights(self):
        """Tests GET /api/comparisons/rfqs/{id}/scoring/ using default 40/30/15/10/5 weights."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/comparisons/rfqs/{self.rfq.id}/scoring/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['rfq_id'], str(self.rfq.id))
        self.assertEqual(len(data['rankings']), 2)
        self.assertEqual(data['weights_applied']['price'], 40.0)

        # Alpha is cheaper ($4500 vs $5000) so Alpha takes rank 1 under price 40%
        self.assertEqual(data['rankings'][0]['supplier_name'], 'Vendor Alpha')
        self.assertEqual(data['rankings'][0]['rank'], 1)
        self.assertEqual(data['rankings'][1]['supplier_name'], 'Vendor Beta')
        self.assertEqual(data['rankings'][1]['rank'], 2)

    def test_api_rfq_scoring_post_custom_weights(self):
        """Tests POST /api/comparisons/rfqs/{id}/scoring/ with customized weights favoring warranty & payment."""
        self.client.force_authenticate(user=self.user)
        payload = {
            'weights': {
                'price': 10.0,
                'spec_match': 20.0,
                'delivery': 10.0,
                'payment_terms': 30.0,  # Favors Beta's Net 60
                'warranty': 30.0,       # Favors Beta's 24 months
            }
        }
        response = self.client.post(f'/api/comparisons/rfqs/{self.rfq.id}/scoring/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Under warranty and payment heavy weights, Beta takes rank 1!
        self.assertEqual(data['rankings'][0]['supplier_name'], 'Vendor Beta')
        self.assertEqual(data['rankings'][0]['rank'], 1)
        self.assertEqual(data['rankings'][1]['supplier_name'], 'Vendor Alpha')
        self.assertEqual(data['rankings'][1]['rank'], 2)

    def test_api_evaluate_raw_scoring(self):
        """Tests POST /api/comparisons/scoring/evaluate-raw/ on raw JSON payloads."""
        self.client.force_authenticate(user=self.user)
        payload = {
            'rfq_data': {
                'rfq_number': 'RAW-RFQ-1',
                'currency': 'USD',
                'items': [],
            },
            'quotations_data': [
                {
                    'quotation_number': 'Q-RAW-1',
                    'supplier_name': 'Raw Supplier A',
                    'total_amount': '1000.00',
                    'payment_terms': 'Net 30',
                    'warranty_information': '12 months',
                },
                {
                    'quotation_number': 'Q-RAW-2',
                    'supplier_name': 'Raw Supplier B',
                    'total_amount': '1200.00',
                    'payment_terms': 'Net 60',
                    'warranty_information': '24 months',
                },
            ],
            'weights': {'price': 40.0, 'spec_match': 30.0, 'delivery': 15.0, 'payment_terms': 10.0, 'warranty': 5.0},
        }

        response = self.client.post('/api/comparisons/scoring/evaluate-raw/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(len(data['rankings']), 2)
        self.assertEqual(data['rankings'][0]['supplier_name'], 'Raw Supplier A')

    def test_tenant_isolation_forbidden_for_other_org(self):
        """User from another organization receives 404 accessing RFQ scoring."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/comparisons/rfqs/{self.rfq.id}/scoring/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
