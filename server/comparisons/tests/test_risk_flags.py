"""
Comprehensive Unit Tests for Quotation Risk Flag Engine in QuoteFlow AI.

Covers:
1. Specification mismatch (SPECIFICATION_MISMATCH)
2. Missing specifications (MISSING_SPECIFICATIONS)
3. Quantity shortfall (QUANTITY_SHORTFALL)
4. Delivery delay (DELIVERY_DELAY)
5. Expired quotation (EXPIRED_QUOTATION)
6. Missing quotation validity (MISSING_QUOTATION_VALIDITY)
7. Payment risk (PAYMENT_RISK)
8. High advance payment (HIGH_ADVANCE_PAYMENT)
9. No warranty (NO_WARRANTY)
10. Missing warranty (MISSING_WARRANTY)
11. Calculation error (CALCULATION_ERROR)
12. Price inconsistency (PRICE_INCONSISTENCY)
13. Missing quotation information (MISSING_QUOTATION_INFORMATION)
14. Currency mismatch (CURRENCY_MISMATCH)
15. Rule configurability & threshold customization
16. Django model ingestion & end-to-end API evaluation
17. Multi-tenant security isolation
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from comparisons.risk import (
    QuotationRiskEngine,
    RiskEngineConfig,
    RiskFlagType,
    RiskSeverity,
)
from organizations.models import Organization, OrganizationMembership
from quotations.models import Quotation, QuotationItem
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier

User = get_user_model()


class QuotationRiskEngineUnitTests(TestCase):
    """Pure-Python deterministic risk rule unit tests."""

    def setUp(self):
        self.engine = QuotationRiskEngine()
        self.today = date(2026, 11, 22)

    def test_specification_mismatch_detected(self):
        """RFQ requires PNP output, but supplier quoted NPN."""
        rfq_data = {
            'items': [
                {
                    'id': 'rfq-item-1',
                    'position': 1,
                    'item_name': 'Proximity Sensor',
                    'custom_specifications': {'Output': 'PNP', 'Voltage': '24V DC'},
                }
            ]
        }
        quote_data = {
            'quotation_number': 'Q-101',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Sensor Co',
            'warranty_information': '12 months standard warranty',
            'payment_terms': 'Net 30 days',
            'line_items': [
                {
                    'rfq_item_id': 'rfq-item-1',
                    'position': 1,
                    'description': 'Proximity Sensor',
                    'quantity': '10',
                    'unit_price': '50.00',
                    'line_total': '500.00',
                    'specifications': {'Output': 'NPN', 'Voltage': '24V DC'},
                }
            ]
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.SPECIFICATION_MISMATCH, flag_types)
        mismatch_flag = next(f for f in report.flags if f.type == RiskFlagType.SPECIFICATION_MISMATCH)
        self.assertEqual(mismatch_flag.severity, RiskSeverity.CRITICAL)
        self.assertIn("PNP", mismatch_flag.evidence)
        self.assertIn("NPN", mismatch_flag.evidence)
        self.assertFalse(report.is_acceptable)

    def test_missing_specifications_detected(self):
        """RFQ requires IP67 rating, but quote omits it."""
        rfq_data = {
            'items': [
                {
                    'id': 'rfq-item-1',
                    'position': 1,
                    'item_name': 'Inductive Sensor',
                    'custom_specifications': {'IP Rating': 'IP67'},
                }
            ]
        }
        quote_data = {
            'quotation_number': 'Q-102',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Sensor Co',
            'warranty_information': '12 months standard warranty',
            'payment_terms': 'Net 30 days',
            'line_items': [
                {
                    'rfq_item_id': 'rfq-item-1',
                    'position': 1,
                    'description': 'Inductive Sensor',
                    'quantity': '10',
                    'unit_price': '50.00',
                    'line_total': '500.00',
                    'specifications': {},  # IP Rating omitted
                }
            ]
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.MISSING_SPECIFICATIONS, flag_types)
        missing_flag = next(f for f in report.flags if f.type == RiskFlagType.MISSING_SPECIFICATIONS)
        self.assertIn("IP Rating", missing_flag.title)

    def test_quantity_shortfall_detected(self):
        """RFQ requested 100 units, but supplier quoted 70 units (30% shortfall)."""
        rfq_data = {
            'items': [
                {
                    'id': 'rfq-item-1',
                    'position': 1,
                    'item_name': 'Steel Flange',
                    'quantity': '100',
                    'unit': 'PCS',
                }
            ]
        }
        quote_data = {
            'quotation_number': 'Q-103',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Foundry Corp',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [
                {
                    'rfq_item_id': 'rfq-item-1',
                    'position': 1,
                    'description': 'Steel Flange',
                    'quantity': '70',
                    'unit': 'PCS',
                    'unit_price': '25.00',
                    'line_total': '1750.00',
                }
            ]
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.QUANTITY_SHORTFALL, flag_types)
        shortfall_flag = next(f for f in report.flags if f.type == RiskFlagType.QUANTITY_SHORTFALL)
        self.assertEqual(shortfall_flag.severity, RiskSeverity.CRITICAL)  # 30% > 20% critical threshold
        self.assertIn("30.0% deficit", shortfall_flag.title)

    def test_delivery_delay_detected(self):
        """Quoted delivery date is 20 days after RFQ required date."""
        rfq_data = {
            'required_delivery_date': '2026-12-01',
        }
        quote_data = {
            'quotation_number': 'Q-104',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'delivery_date': '2026-12-21',  # 20 days delay
            'supplier_name': 'Global Logistics Corp',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.DELIVERY_DELAY, flag_types)
        delay_flag = next(f for f in report.flags if f.type == RiskFlagType.DELIVERY_DELAY)
        self.assertEqual(delay_flag.severity, RiskSeverity.CRITICAL)  # 20 days >= 14 days critical threshold
        self.assertIn("20 days late", delay_flag.title)

    def test_expired_quotation_detected(self):
        """Quotation expired 7 days ago."""
        quote_data = {
            'quotation_number': 'Q-105',
            'quotation_date': '2026-10-01',
            'validity_date': '2026-11-15',  # Expired relative to 2026-11-22
            'supplier_name': 'Apex Metals',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.EXPIRED_QUOTATION, flag_types)
        exp_flag = next(f for f in report.flags if f.type == RiskFlagType.EXPIRED_QUOTATION)
        self.assertEqual(exp_flag.severity, RiskSeverity.CRITICAL)
        self.assertIn("7 days ago", exp_flag.description)

    def test_missing_quotation_validity_detected(self):
        """Quotation validity date is omitted."""
        quote_data = {
            'quotation_number': 'Q-106',
            'quotation_date': '2026-11-20',
            'validity_date': None,
            'supplier_name': 'Apex Metals',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.MISSING_QUOTATION_VALIDITY, flag_types)
        val_flag = next(f for f in report.flags if f.type == RiskFlagType.MISSING_QUOTATION_VALIDITY)
        self.assertEqual(val_flag.severity, RiskSeverity.WARNING)

    def test_payment_risk_terms_detected(self):
        """Cash on Delivery (COD) payment risk."""
        quote_data = {
            'quotation_number': 'Q-107',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Rapid Tooling',
            'warranty_information': '12 months',
            'payment_terms': 'Terms: Cash on Delivery (COD)',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.PAYMENT_RISK, flag_types)
        pay_flag = next(f for f in report.flags if f.type == RiskFlagType.PAYMENT_RISK)
        self.assertEqual(pay_flag.severity, RiskSeverity.WARNING)

    def test_high_advance_payment_detected(self):
        """100% advance payment demanded."""
        quote_data = {
            'quotation_number': 'Q-108',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Overseas Fab Ltd',
            'warranty_information': '12 months',
            'payment_terms': '100% advance payment before dispatch',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.HIGH_ADVANCE_PAYMENT, flag_types)
        adv_flag = next(f for f in report.flags if f.type == RiskFlagType.HIGH_ADVANCE_PAYMENT)
        self.assertEqual(adv_flag.severity, RiskSeverity.CRITICAL)
        self.assertIn("100%", adv_flag.title)

    def test_no_warranty_disclaimer_detected(self):
        """Explicit disclaimer of warranty (as-is terms)."""
        quote_data = {
            'quotation_number': 'Q-109',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Surplus Machinery',
            'warranty_information': 'Sold as-is, with no warranty or return guarantee.',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.NO_WARRANTY, flag_types)
        nowar_flag = next(f for f in report.flags if f.type == RiskFlagType.NO_WARRANTY)
        self.assertEqual(nowar_flag.severity, RiskSeverity.CRITICAL)

    def test_missing_warranty_detected(self):
        """Quotation omits warranty terms entirely."""
        quote_data = {
            'quotation_number': 'Q-110',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Standard Supplies',
            'warranty_information': '',  # Empty
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.MISSING_WARRANTY, flag_types)
        miswar_flag = next(f for f in report.flags if f.type == RiskFlagType.MISSING_WARRANTY)
        self.assertEqual(miswar_flag.severity, RiskSeverity.WARNING)

    def test_calculation_error_detected(self):
        """Line total stated as 550.00, but 10 * 50.00 = 500.00."""
        quote_data = {
            'quotation_number': 'Q-111',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Faulty Math Inc',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [
                {
                    'position': 1,
                    'description': 'Machined Gear',
                    'quantity': '10',
                    'unit_price': '50.00',
                    'discount': '0.00',
                    'tax': '0.00',
                    'line_total': '550.00',  # Error: Should be 500.00
                }
            ],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.CALCULATION_ERROR, flag_types)
        calc_flag = next(f for f in report.flags if f.type == RiskFlagType.CALCULATION_ERROR)
        self.assertEqual(calc_flag.severity, RiskSeverity.CRITICAL)
        self.assertIn("550.00", calc_flag.evidence)
        self.assertIn("500.00", calc_flag.evidence)

    def test_price_inconsistency_negative_and_surge(self):
        """Negative price and target price surge detection."""
        rfq_data = {
            'items': [
                {
                    'id': 'rfq-item-1',
                    'position': 1,
                    'item_name': 'Precision Bearing',
                    'target_unit_price': '100.00',
                }
            ]
        }
        quote_data = {
            'quotation_number': 'Q-112',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'High Price Co',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [
                {
                    'rfq_item_id': 'rfq-item-1',
                    'position': 1,
                    'description': 'Precision Bearing',
                    'quantity': '5',
                    'unit_price': '250.00',  # 150% above target 100.00
                    'line_total': '1250.00',
                }
            ],
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.PRICE_INCONSISTENCY, flag_types)
        price_flag = next(f for f in report.flags if f.type == RiskFlagType.PRICE_INCONSISTENCY)
        self.assertIn("Surge", price_flag.title)
        self.assertIn("+150.0%", price_flag.title)

    def test_missing_quotation_information_detected(self):
        """Missing quotation number, quotation date, and supplier name."""
        quote_data = {
            'quotation_number': '',
            'quotation_date': None,
            'supplier_name': '',
            'validity_date': '2026-12-20',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        admin_flags = [f for f in report.flags if f.type == RiskFlagType.MISSING_QUOTATION_INFORMATION]

        self.assertGreaterEqual(len(admin_flags), 3)
        fields = {f.affected_field_or_item for f in admin_flags}
        self.assertIn("quotation_number", fields)
        self.assertIn("quotation_date", fields)
        self.assertIn("supplier", fields)

    def test_currency_mismatch_detected(self):
        """RFQ in USD, but quote submitted in EUR."""
        rfq_data = {
            'currency': 'USD',
        }
        quote_data = {
            'quotation_number': 'Q-114',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'currency': 'EUR',
            'supplier_name': 'Eurotech GmbH',
            'warranty_information': '12 months',
            'payment_terms': 'Net 30',
            'line_items': [],
        }

        report = self.engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        flag_types = [f.type for f in report.flags]

        self.assertIn(RiskFlagType.CURRENCY_MISMATCH, flag_types)
        curr_flag = next(f for f in report.flags if f.type == RiskFlagType.CURRENCY_MISMATCH)
        self.assertIn("EUR", curr_flag.title)
        self.assertIn("USD", curr_flag.title)

    def test_configurable_thresholds_override(self):
        """Custom threshold config overrides defaults."""
        custom_config = RiskEngineConfig(
            advance_payment_warning_threshold_pct=20.0,
            advance_payment_critical_threshold_pct=40.0,
        )
        custom_engine = QuotationRiskEngine(config=custom_config)

        quote_data = {
            'quotation_number': 'Q-115',
            'quotation_date': '2026-11-20',
            'validity_date': '2026-12-20',
            'supplier_name': 'Custom Terms Corp',
            'warranty_information': '12 months',
            'payment_terms': '45% advance payment required',  # Critical under custom (40%), warning under default (50%)
            'line_items': [],
        }

        report = custom_engine.evaluate_quotation(quote_data, evaluation_date=self.today)
        adv_flag = next(f for f in report.flags if f.type == RiskFlagType.HIGH_ADVANCE_PAYMENT)
        self.assertEqual(adv_flag.severity, RiskSeverity.CRITICAL)

    def test_rule_filtering_with_enabled_rules(self):
        """Only enabled rules are evaluated."""
        restricted_config = RiskEngineConfig(
            enabled_rules={RiskFlagType.CURRENCY_MISMATCH}
        )
        restricted_engine = QuotationRiskEngine(config=restricted_config)

        rfq_data = {'currency': 'USD'}
        quote_data = {
            'quotation_number': '',  # Would normally trigger MISSING_QUOTATION_INFORMATION
            'currency': 'JPY',
            'validity_date': None,  # Would normally trigger MISSING_QUOTATION_VALIDITY
            'payment_terms': '100% advance',  # Would normally trigger HIGH_ADVANCE_PAYMENT
            'warranty_information': '',  # Would normally trigger MISSING_WARRANTY
            'line_items': [],
        }

        report = restricted_engine.evaluate_quotation(quote_data, rfq_data, evaluation_date=self.today)
        self.assertEqual(len(report.flags), 1)
        self.assertEqual(report.flags[0].type, RiskFlagType.CURRENCY_MISMATCH)


class DjangoModelAndAPIRiskTests(TestCase):
    """Integration tests evaluating Django models and REST API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='risk_auditor@example.com',
            password='StrongPassword123!',
        )
        self.other_user = User.objects.create_user(
            email='unauthorized@othercorp.com',
            password='StrongPassword123!',
        )

        self.org = Organization.objects.create(name='Risk Assessment Org', slug='risk-assess-org')
        self.other_org = Organization.objects.create(name='Other Org', slug='other-org-risk')

        OrganizationMembership.objects.create(user=self.user, organization=self.org, role='admin')
        OrganizationMembership.objects.create(user=self.other_user, organization=self.other_org, role='admin')

        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Risky Supplies Co',
            email='sales@riskysupplies.com',
        )

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-RISK-2026-001',
            title='Industrial Valve Procurement',
            currency='USD',
            status=RFQStatus.OPEN,
            required_delivery_date=date(2026, 12, 1),
            created_by=self.user,
        )

        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name='Ball Valve 2-inch',
            quantity=Decimal('20.0000'),
            unit='PCS',
            target_unit_price=Decimal('100.00'),
            custom_specifications={'Material': 'SS 316'},
        )

        # Quotation with intentional risks:
        # - Expired validity
        # - High advance payment (100%)
        # - Material mismatch (SS 304 instead of SS 316)
        # - Quantity shortfall (15 instead of 20)
        # - Missing warranty
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='QUO-RISK-771',
            quotation_date=date(2026, 10, 1),
            validity_date=date(2026, 10, 31),  # Expired
            currency='USD',
            payment_terms='100% advance payment required prior to manufacturing',
            warranty_information='',  # Missing
            subtotal=Decimal('1500.00'),
            total_amount=Decimal('1500.00'),
            status='received',
        )

        self.quote_item = QuotationItem.objects.create(
            quotation=self.quotation,
            rfq_item=self.rfq_item,
            position=1,
            description='Ball Valve 2-inch Industrial',
            quantity=Decimal('15.0000'),  # 15 vs 20 (shortfall)
            unit='PCS',
            unit_price=Decimal('100.00'),
            line_total=Decimal('1500.00'),
            specifications={'Material': 'SS 304'},  # Mismatch
        )

    def test_django_model_risk_evaluation(self):
        """Tests QuotationRiskEngine on Django model instances."""
        engine = QuotationRiskEngine()
        report = engine.evaluate_quotation(
            quotation_or_data=self.quotation,
            rfq_or_data=self.rfq,
            evaluation_date=date(2026, 11, 22),
        )

        self.assertEqual(report.quotation_id, str(self.quotation.id))
        self.assertEqual(report.supplier_name, 'Risky Supplies Co')
        self.assertFalse(report.is_acceptable)
        self.assertEqual(report.overall_risk_level, 'CRITICAL')

        flag_types = {f.type for f in report.flags}
        self.assertIn(RiskFlagType.EXPIRED_QUOTATION, flag_types)
        self.assertIn(RiskFlagType.HIGH_ADVANCE_PAYMENT, flag_types)
        self.assertIn(RiskFlagType.SPECIFICATION_MISMATCH, flag_types)
        self.assertIn(RiskFlagType.QUANTITY_SHORTFALL, flag_types)
        self.assertIn(RiskFlagType.MISSING_WARRANTY, flag_types)

    def test_api_quotation_risk_flags_get(self):
        """Tests GET /api/comparisons/quotations/{id}/risk-flags/."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/comparisons/quotations/{self.quotation.id}/risk-flags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['quotation_id'], str(self.quotation.id))
        self.assertEqual(data['overall_risk_level'], 'CRITICAL')
        self.assertGreaterEqual(data['critical_count'], 2)

    def test_api_rfq_risk_flags_get(self):
        """Tests GET /api/comparisons/rfqs/{id}/risk-flags/."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/comparisons/rfqs/{self.rfq.id}/risk-flags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['quotation_number'], 'QUO-RISK-771')

    def test_api_evaluate_raw_risk(self):
        """Tests POST /api/comparisons/risk-flags/evaluate-raw/ with raw payload."""
        self.client.force_authenticate(user=self.user)
        payload = {
            'quotation_data': {
                'quotation_number': 'RAW-99',
                'quotation_date': '2026-11-20',
                'validity_date': '2026-12-20',
                'payment_terms': '50% advance, 50% on delivery',
                'warranty_information': '12 months',
                'currency': 'EUR',
                'line_items': [],
            },
            'rfq_data': {
                'currency': 'USD',
            },
            'evaluation_date': '2026-11-22',
        }

        response = self.client.post('/api/comparisons/risk-flags/evaluate-raw/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        flag_types = [f['type'] for f in data['flags']]
        self.assertIn('currency_mismatch', flag_types)
        self.assertIn('high_advance_payment', flag_types)

    def test_tenant_isolation_forbidden_for_other_org(self):
        """Other organization user receives 404 for accessing other tenant quotation risk."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/comparisons/quotations/{self.quotation.id}/risk-flags/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
