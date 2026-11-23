"""
Comprehensive Unit Tests for Technical Specification Matching Engine in QuoteFlow AI.

Covers:
1. User's exact Proximity Sensor example (24V DC, PNP vs NPN, 8mm, M12)
2. Exact matches (units, voltage ranges, synonyms, IP ratings)
3. Mismatches (electrical polarity, AC vs DC, dimension variance, contact state, material grades)
4. Missing specifications (RFQ mandatory requirement omitted by supplier)
5. Unclear specifications (ambiguous terms: "standard", "catalog", "TBD")
6. Additional specifications (supplier quotation offers bonus features not in RFQ)
7. AI Safety Guardrails (no silent match claims, low confidence demoted to UNCLEAR, graceful fallback)
8. Django Model Integration (RFQItem, RFQItemSpecification, QuotationItem)
9. API Endpoints (POST /api/comparisons/match-specs/, GET /api/comparisons/rfqs/{id}/specs/)
10. Multi-tenant isolation security
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from comparisons.specs import (
    AISpecMatcher,
    DeterministicSpecMatcher,
    DiscrepancySeverity,
    ItemSpecMatchSummary,
    SingleSpecMatchResult,
    SpecificationMatchingEngine,
    SpecImportance,
    SpecMatchStatus,
    SpecVerdict,
)
from comparisons.specs.ai_matcher import AISpecEvaluationSchema
from organizations.models import Organization, OrganizationMembership
from quotations.models import Quotation, QuotationItem
from rfqs.models import RFQ, RFQItem, RFQItemSpecification, RFQStatus, SpecificationImportance
from suppliers.models import Supplier

User = get_user_model()


class SpecificationMatchingEngineTests(TestCase):
    """Core deterministic and AI-assisted specification matching tests."""

    def setUp(self):
        self.engine = SpecificationMatchingEngine()
        self.rules = DeterministicSpecMatcher()

    def test_user_exact_example_proximity_sensor(self):
        """
        Tests user's exact specification example:
        RFQ:
          - Voltage: 24V DC
          - Output: PNP
          - Sensing distance: 8mm
          - Connection: M12
        Supplier:
          - Voltage: 24V DC
          - Output: NPN
          - Sensing distance: 8mm
          - Connection: M12

        Expected:
          - Voltage: EXACT_MATCH
          - Output: MISMATCH (critical polarity conflict sourcing vs sinking)
          - Sensing distance: EXACT_MATCH
          - Connection: EXACT_MATCH
          - Score: 75.0%
          - Verdict: NON_COMPLIANT (critical mismatch)
        """
        rfq_specs = {
            'Voltage': '24V DC',
            'Output': 'PNP',
            'Sensing distance': '8mm',
            'Connection': 'M12',
        }

        supplier_specs = {
            'Voltage': '24V DC',
            'Output': 'NPN',
            'Sensing distance': '8mm',
            'Connection': 'M12',
        }

        summary = self.engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=supplier_specs,
            item_name='Proximity Sensor',
        )

        self.assertEqual(summary.item_name, 'Proximity Sensor')
        self.assertEqual(summary.total_requirements_count, 4)
        self.assertEqual(summary.exact_matches_count, 3)
        self.assertEqual(summary.mismatches_count, 1)
        self.assertEqual(summary.missing_count, 0)
        self.assertEqual(summary.unclear_count, 0)
        self.assertEqual(summary.additional_count, 0)
        self.assertEqual(summary.spec_match_score, 75.0)
        self.assertTrue(summary.has_critical_mismatches)
        self.assertEqual(summary.verdict, SpecVerdict.NON_COMPLIANT)

        # Inspect individual match records
        results_by_key = {m.canonical_key: m for m in summary.matches}

        # Voltage
        volt_res = results_by_key['voltage']
        self.assertEqual(volt_res.status, SpecMatchStatus.EXACT_MATCH)
        self.assertEqual(volt_res.severity, DiscrepancySeverity.NONE)
        self.assertTrue(volt_res.is_deterministic)

        # Output: critical mismatch
        out_res = results_by_key['output']
        self.assertEqual(out_res.status, SpecMatchStatus.MISMATCH)
        self.assertEqual(out_res.severity, DiscrepancySeverity.CRITICAL)
        self.assertIn("sourcing", out_res.explanation.lower())
        self.assertIn("sinking", out_res.explanation.lower())
        self.assertEqual(out_res.requirement_value, 'PNP')
        self.assertEqual(out_res.supplier_value, 'NPN')

        # Sensing distance
        dist_res = results_by_key['sensing_distance']
        self.assertEqual(dist_res.status, SpecMatchStatus.EXACT_MATCH)
        self.assertEqual(dist_res.severity, DiscrepancySeverity.NONE)

        # Connection
        conn_res = results_by_key['connection']
        self.assertEqual(conn_res.status, SpecMatchStatus.EXACT_MATCH)
        self.assertEqual(conn_res.severity, DiscrepancySeverity.NONE)

    def test_missing_specification_identified(self):
        """RFQ requires IP rating, but supplier omits it."""
        rfq_specs = {
            'Voltage': '24V DC',
            'IP Rating': {'value': 'IP67', 'importance': 'mandatory'},
        }
        supplier_specs = {
            'Voltage': '24V DC',
        }

        summary = self.engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=supplier_specs,
        )

        self.assertEqual(summary.total_requirements_count, 2)
        self.assertEqual(summary.exact_matches_count, 1)
        self.assertEqual(summary.missing_count, 1)
        self.assertEqual(summary.verdict, SpecVerdict.INCOMPLETE)

        missing_item = next(m for m in summary.matches if m.canonical_key == 'ip_rating')
        self.assertEqual(missing_item.status, SpecMatchStatus.MISSING)
        self.assertIsNone(missing_item.supplier_value)
        self.assertIn("omitted", missing_item.explanation)
        self.assertEqual(missing_item.severity, DiscrepancySeverity.CRITICAL)

    def test_unclear_specification_identified(self):
        """Supplier provides vague or placeholder values like 'standard' or 'see datasheet'."""
        rfq_specs = {
            'Connection': 'M12 4-pin',
            'Housing Material': 'Stainless Steel 316',
        }
        supplier_specs = {
            'Connection': 'Standard connector',
            'Housing Material': 'See datasheet',
        }

        summary = self.engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=supplier_specs,
        )

        self.assertEqual(summary.unclear_count, 2)
        self.assertEqual(summary.verdict, SpecVerdict.SPEC_VARIANCE)

        conn_item = next(m for m in summary.matches if m.canonical_key == 'connection')
        self.assertEqual(conn_item.status, SpecMatchStatus.UNCLEAR)
        self.assertIn("ambiguous", conn_item.explanation.lower())

    def test_additional_specifications_identified(self):
        """Supplier offers extra technical specifications not requested in RFQ."""
        rfq_specs = {
            'Voltage': '24V DC',
        }
        supplier_specs = {
            'Voltage': '24V DC',
            'Switching Frequency': '1500 Hz',
            'Short Circuit Protection': 'Pulsed',
        }

        summary = self.engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=supplier_specs,
        )

        self.assertEqual(summary.exact_matches_count, 1)
        self.assertEqual(summary.additional_count, 2)
        self.assertEqual(summary.spec_match_score, 100.0)
        self.assertEqual(summary.verdict, SpecVerdict.COMPLIANT)

        add_matches = [m for m in summary.matches if m.status == SpecMatchStatus.ADDITIONAL]
        self.assertEqual(len(add_matches), 2)
        for m in add_matches:
            self.assertEqual(m.severity, DiscrepancySeverity.INFO)
            self.assertIsNone(m.requirement_value)
            self.assertIsNotNone(m.supplier_value)

    def test_voltage_range_and_dc_compatibility(self):
        """Supplier wide range (10-30V DC) matches RFQ 24V DC requirement."""
        res = self.rules.match_specification(
            parameter_name='Operating Voltage',
            requirement_value='24V DC',
            supplier_value='10-30 VDC',
        )
        self.assertEqual(res.status, SpecMatchStatus.EXACT_MATCH)
        self.assertIn("within supplier's operating range", res.explanation.lower())

        # AC vs DC mismatch
        res_ac = self.rules.match_specification(
            parameter_name='Operating Voltage',
            requirement_value='24V DC',
            supplier_value='230V AC',
        )
        self.assertEqual(res_ac.status, SpecMatchStatus.MISMATCH)
        self.assertEqual(res_ac.severity, DiscrepancySeverity.CRITICAL)

    def test_distance_dimension_normalization(self):
        """Tests metric conversion: 0.8 cm matches 8 mm; 12mm mismatches 8mm."""
        res_cm = self.rules.match_specification(
            parameter_name='Sensing Distance',
            requirement_value='8mm',
            supplier_value='0.8 cm',
        )
        self.assertEqual(res_cm.status, SpecMatchStatus.EXACT_MATCH)

        res_diff = self.rules.match_specification(
            parameter_name='Sensing Distance',
            requirement_value='8mm',
            supplier_value='12mm',
        )
        self.assertEqual(res_diff.status, SpecMatchStatus.MISMATCH)
        self.assertIn("mismatch", res_diff.explanation.lower())

    def test_ip_ratings_comparison(self):
        """IP68 satisfies IP67 requirement; IP65 fails IP67 requirement."""
        res_higher = self.rules.match_specification(
            parameter_name='Ingress Protection',
            requirement_value='IP67',
            supplier_value='IP 68',
        )
        self.assertEqual(res_higher.status, SpecMatchStatus.EXACT_MATCH)
        self.assertIn("exceeds", res_higher.explanation.lower())

        res_lower = self.rules.match_specification(
            parameter_name='Ingress Protection',
            requirement_value='IP67',
            supplier_value='IP65',
        )
        self.assertEqual(res_lower.status, SpecMatchStatus.MISMATCH)
        self.assertIn("liquid ingress protection", res_lower.explanation.lower())

    def test_material_grades_comparison(self):
        """Stainless Steel 316 vs SS 304 conflict."""
        res = self.rules.match_specification(
            parameter_name='Material',
            requirement_value='Stainless Steel 316L',
            supplier_value='SS 304',
        )
        self.assertEqual(res.status, SpecMatchStatus.MISMATCH)
        self.assertIn("corrosion resistance", res.explanation.lower())

        # Exact synonym match
        res_syn = self.rules.match_specification(
            parameter_name='Material',
            requirement_value='Stainless Steel 316',
            supplier_value='SS316',
        )
        self.assertEqual(res_syn.status, SpecMatchStatus.EXACT_MATCH)

    def test_contact_logic_matching(self):
        """Normally Open (NO) vs Normally Closed (NC); NO vs NO+NC."""
        res_conflict = self.rules.match_specification(
            parameter_name='Contact Configuration',
            requirement_value='Normally Open (NO)',
            supplier_value='NC',
        )
        self.assertEqual(res_conflict.status, SpecMatchStatus.MISMATCH)

        res_complementary = self.rules.match_specification(
            parameter_name='Contact Configuration',
            requirement_value='NO',
            supplier_value='1 NO + 1 NC',
        )
        self.assertEqual(res_complementary.status, SpecMatchStatus.EXACT_MATCH)


class AISpecMatcherSafetyTests(TestCase):
    """
    Tests ensuring AI semantic matching complies with strict safety rules:
    - Never silently claims a match
    - Demotes low confidence (< 0.85) to UNCLEAR
    - Gracefully falls back when API fails
    """

    def test_ai_low_confidence_match_demoted_to_unclear(self):
        """When Gemini returns 'exact_match' but confidence is 0.70, system enforces UNCLEAR."""
        mock_gemini = MagicMock()
        mock_gemini.generate_structured.return_value = AISpecEvaluationSchema(
            status='exact_match',
            confidence=0.70,  # Below 0.85 safety threshold
            explanation="Phrases look somewhat similar but might have subtle differences.",
            evidence="Quoted text",
        )

        matcher = AISpecMatcher(gemini_service=mock_gemini)
        result = matcher.evaluate_specification(
            parameter_name="Custom Coating",
            requirement_value="Type A anodized",
            supplier_value="Black finish",
        )

        # Enforces UNCLEAR despite AI's status claim
        self.assertEqual(result.status, SpecMatchStatus.UNCLEAR)
        self.assertIn("below the safety threshold", result.explanation)
        self.assertFalse(result.is_deterministic)

    def test_ai_high_confidence_match_accepted(self):
        """When Gemini returns 'exact_match' with confidence 0.95, it is accepted."""
        mock_gemini = MagicMock()
        mock_gemini.generate_structured.return_value = AISpecEvaluationSchema(
            status='exact_match',
            confidence=0.95,
            explanation="Polycarbonate is the exact chemical name for PC plastic casing.",
            evidence="PC casing",
            technical_notes="Standard polymer equivalence",
        )

        matcher = AISpecMatcher(gemini_service=mock_gemini)
        result = matcher.evaluate_specification(
            parameter_name="Enclosure Material",
            requirement_value="Polycarbonate",
            supplier_value="PC casing",
        )

        self.assertEqual(result.status, SpecMatchStatus.EXACT_MATCH)
        self.assertIn("Polycarbonate is the exact chemical name", result.explanation)
        self.assertEqual(result.confidence, 0.95)
        self.assertIn("Standard polymer equivalence", result.explanation)

    def test_ai_mismatch_strictly_preserved(self):
        """When Gemini identifies a mismatch, it is marked as MISMATCH with CRITICAL severity for mandatory."""
        mock_gemini = MagicMock()
        mock_gemini.generate_structured.return_value = AISpecEvaluationSchema(
            status='mismatch',
            confidence=0.98,
            explanation="Thread pitch M12x1.5 does not mate with standard metric fine M12x1.0.",
            evidence="M12x1.5",
        )

        matcher = AISpecMatcher(gemini_service=mock_gemini)
        result = matcher.evaluate_specification(
            parameter_name="Thread Spec",
            requirement_value="M12x1.0",
            supplier_value="M12x1.5",
            importance=SpecImportance.MANDATORY,
        )

        self.assertEqual(result.status, SpecMatchStatus.MISMATCH)
        self.assertEqual(result.severity, DiscrepancySeverity.CRITICAL)

    def test_ai_service_exception_safe_fallback(self):
        """When Gemini throws an API exception, system safely returns UNCLEAR rather than crashing."""
        mock_gemini = MagicMock()
        mock_gemini.generate_structured.side_effect = RuntimeError("Gemini 429 Quota Exceeded")

        matcher = AISpecMatcher(gemini_service=mock_gemini)
        result = matcher.evaluate_specification(
            parameter_name="Coating",
            requirement_value="Galvanized",
            supplier_value="Zinc Electroplated",
        )

        self.assertEqual(result.status, SpecMatchStatus.UNCLEAR)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("could not complete", result.explanation)


class DjangoModelAndAPIIntegrationTests(TestCase):
    """Tests specification matching integration with Django RFQ and Quotation models and APIs."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='procurement@example.com',
            password='StrongPassword123!',
            first_name='Elena',
            last_name='Rostova',
        )
        self.other_user = User.objects.create_user(
            email='outsider@othercorp.com',
            password='StrongPassword123!',
        )

        self.org = Organization.objects.create(name='AeroTech Industries', slug='aerotech-spec-test')
        self.other_org = Organization.objects.create(name='Rival Corp', slug='rival-corp-spec-test')

        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.org,
            role='admin',
        )
        OrganizationMembership.objects.create(
            user=self.other_user,
            organization=self.other_org,
            role='admin',
        )

        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Precision Sensors Ltd',
            email='sales@precisionsensors.com',
        )

        # Create RFQ with proximity sensor requirement
        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-SENS-2026-001',
            title='Inductive Proximity Sensors Procurement',
            currency='USD',
            status=RFQStatus.OPEN,
            created_by=self.user,
        )

        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name='Proximity sensor',
            quantity=Decimal('50.0000'),
            unit='PCS',
            target_unit_price=Decimal('25.00'),
            custom_specifications={
                'Voltage': '24V DC',
                'Output': 'PNP',
                'Sensing distance': '8mm',
                'Connection': 'M12',
            },
        )

        # Add explicit relational specification
        RFQItemSpecification.objects.create(
            item=self.rfq_item,
            parameter_name='IP Rating',
            required_value='IP67',
            importance=SpecificationImportance.MANDATORY,
        )

        # Create supplier quotation
        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='QUO-PS-9921',
            currency='USD',
            status='under_review',
        )

        self.quote_item = QuotationItem.objects.create(
            quotation=self.quotation,
            rfq_item=self.rfq_item,
            position=1,
            description='Inductive Proximity Sensor M12',
            quantity=Decimal('50.0000'),
            unit='PCS',
            unit_price=Decimal('22.50'),
            line_total=Decimal('1125.00'),
            specifications={
                'Voltage': '24V DC',
                'Output': 'NPN',  # Polarity mismatch
                'Sensing distance': '8mm',
                'Connection': 'M12',
                'IP Rating': 'IP67',
                'Extra Feature': 'LED Indicator',  # Additional
            },
        )

    def test_database_model_spec_extraction_and_matching(self):
        """Verifies that engine directly ingests RFQItem and QuotationItem models."""
        engine = SpecificationMatchingEngine()
        summary = engine.compare_item_specifications(
            rfq_item_or_specs=self.rfq_item,
            supplier_item_or_specs=self.quote_item,
        )

        self.assertEqual(summary.rfq_item_id, str(self.rfq_item.id))
        self.assertEqual(summary.quotation_item_id, str(self.quote_item.id))
        self.assertEqual(summary.supplier_name, 'Precision Sensors Ltd')

        # 4 from custom_specifications + 1 from RFQItemSpecification = 5 total requirements
        self.assertEqual(summary.total_requirements_count, 5)
        self.assertEqual(summary.exact_matches_count, 4)  # Voltage, Sensing dist, Connection, IP67
        self.assertEqual(summary.mismatches_count, 1)     # PNP vs NPN
        self.assertEqual(summary.additional_count, 1)     # LED Indicator
        self.assertTrue(summary.has_critical_mismatches)
        self.assertEqual(summary.verdict, SpecVerdict.NON_COMPLIANT)

    def test_api_match_specs_raw_dictionary(self):
        """Tests POST /api/comparisons/match-specs/ with raw dictionaries."""
        self.client.force_authenticate(user=self.user)
        payload = {
            'item_name': 'Proximity sensor',
            'rfq_specs': {
                'Voltage': '24V DC',
                'Output': 'PNP',
                'Sensing distance': '8mm',
                'Connection': 'M12',
            },
            'supplier_specs': {
                'Voltage': '24V DC',
                'Output': 'NPN',
                'Sensing distance': '8mm',
                'Connection': 'M12',
            },
            'use_ai': False,
        }

        response = self.client.post('/api/comparisons/match-specs/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['item_name'], 'Proximity sensor')
        self.assertEqual(data['total_requirements_count'], 4)
        self.assertEqual(data['exact_matches_count'], 3)
        self.assertEqual(data['mismatches_count'], 1)
        self.assertEqual(data['spec_match_score'], 75.0)
        self.assertTrue(data['has_critical_mismatches'])

    def test_api_match_specs_database_ids(self):
        """Tests POST /api/comparisons/match-specs/ with rfq_item_id and quotation_item_id."""
        self.client.force_authenticate(user=self.user)
        payload = {
            'rfq_item_id': str(self.rfq_item.id),
            'quotation_item_id': str(self.quote_item.id),
        }

        response = self.client.post('/api/comparisons/match-specs/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['rfq_item_id'], str(self.rfq_item.id))
        self.assertEqual(data['supplier_name'], 'Precision Sensors Ltd')

    def test_api_compare_rfq_specifications_get(self):
        """Tests GET /api/comparisons/rfqs/{id}/specs/ for whole-RFQ evaluation."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/comparisons/rfqs/{self.rfq.id}/specs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data['rfq_id'], str(self.rfq.id))
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(len(data['supplier_summaries']), 1)

        supp_sum = data['supplier_summaries'][0]
        self.assertEqual(supp_sum['supplier_name'], 'Precision Sensors Ltd')
        self.assertEqual(supp_sum['overall_verdict'], 'non_compliant')
        self.assertEqual(supp_sum['total_critical_mismatches'], 1)

    def test_tenant_isolation_forbidden_for_other_org(self):
        """Other organization user cannot access RFQ specs."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f'/api/comparisons/rfqs/{self.rfq.id}/specs/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
