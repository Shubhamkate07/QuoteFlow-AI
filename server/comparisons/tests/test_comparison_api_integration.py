"""
Integration Test Suite for QuoteFlow AI Comparison Engine APIs.
Tests end-to-end integration across:
- Generate comparison for an RFQ
- Retrieve comparison results
- View supplier comparison results
- View price comparison
- View specification matching
- View risk flags
- View scoring
- View scoring weights
- Update comparison weights
- Regenerate comparison
- Enforcement of approved vs unreviewed quotation data
- Organization tenant isolation
- Permissions & validation
"""
from datetime import date, timedelta
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import BaseModel
from extractions.models import QuotationExtraction, ReviewStatus
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from quotations.models import Quotation, QuotationItem, QuotationStatus, QuotationDocument
from rfqs.models import RFQ, RFQItem, RFQStatus
from suppliers.models import Supplier
from comparisons.models import RFQComparisonSetting, RFQComparisonSnapshot
from comparisons.scoring.weights import DEFAULT_SCORING_WEIGHTS

User = get_user_model()


class ComparisonAPIIntegrationTests(APITestCase):
    """Integration test suite for all RFQ comparison REST APIs."""

    def setUp(self):
        # 1. Organization A (Tenant Alpha)
        self.org_a = Organization.objects.create(
            name="Alpha Aerospace",
            slug=f"alpha-aero-{uuid.uuid4().hex[:8]}",
        )
        self.user_a = User.objects.create_user(
            email=f"procurement-a-{uuid.uuid4().hex[:6]}@alpha.com",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="Procurement",
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationRole.ADMIN,
            is_active=True,
        )

        # 2. Organization B (Tenant Beta - Cross Tenant Attacker)
        self.org_b = Organization.objects.create(
            name="Beta Motors",
            slug=f"beta-motors-{uuid.uuid4().hex[:8]}",
        )
        self.user_b = User.objects.create_user(
            email=f"procurement-b-{uuid.uuid4().hex[:6]}@beta.com",
            password="SecurePassword123!",
            first_name="Bob",
            last_name="Beta",
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationRole.ADMIN,
            is_active=True,
        )

        # 3. Suppliers in Org A
        self.supplier_1 = Supplier.objects.create(
            organization=self.org_a,
            company_name="Apex Precision Engineering",
            email="sales@apex.com",
            contact_person="Alice Apex",
        )
        self.supplier_2 = Supplier.objects.create(
            organization=self.org_a,
            company_name="Vanguard Dynamics",
            email="quotes@vanguard.com",
            contact_person="Victor Vanguard",
        )
        self.supplier_3 = Supplier.objects.create(
            organization=self.org_a,
            company_name="RawUnreviewed Tech",
            email="ai@rawtech.com",
            contact_person="Ron Raw",
        )

        # 4. Target RFQ in Org A
        self.today = date.today()
        self.rfq = RFQ.objects.create(
            organization=self.org_a,
            rfq_number=f"RFQ-TEST-{uuid.uuid4().hex[:6].upper()}",
            title="High-Precision Hydraulic Valve Assembly",
            currency="USD",
            required_delivery_date=self.today + timedelta(days=30),
            status=RFQStatus.OPEN,
            created_by=self.user_a,
        )
        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name="Hydraulic Valve 350bar",
            description="350 bar proportional valve, 24V DC, 4-20mA control",
            quantity=Decimal('5'),
            unit="PCS",
            target_unit_price=Decimal('500.00'),
            custom_specifications={
                'Pressure': '350 bar',
                'Voltage': '24V DC',
                'Signal': '4-20mA',
            },
        )

        # 5. Quotation 1: Approved Quotation (originated from AI extraction, verified & approved by Alice)
        self.quote_1 = Quotation.objects.create(
            organization=self.org_a,
            rfq=self.rfq,
            supplier=self.supplier_1,
            quotation_number="APEX-QUOTE-101",
            quotation_date=self.today - timedelta(days=2),
            validity_date=self.today + timedelta(days=60),
            currency="USD",
            subtotal=Decimal('2250.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('2250.00'),
            payment_terms="Net 30 days",
            warranty_information="24 months manufacturer warranty",
            delivery_terms="DAP Austin",
            lead_time_weeks=Decimal('3.0'),
            status=QuotationStatus.RECEIVED,
        )
        QuotationItem.objects.create(
            quotation=self.quote_1,
            position=1,
            rfq_item_id=self.rfq_item.id,
            description="Hydraulic Proportional Valve 350bar",
            quantity=Decimal('5'),
            unit="PCS",
            unit_price=Decimal('450.00'),
            line_total=Decimal('2250.00'),
            specifications={
                'Pressure': '350 bar',
                'Voltage': '24V DC',
                'Signal': '4-20mA',
            },
        )
        doc_1 = QuotationDocument.objects.create(
            organization=self.org_a,
            quotation=self.quote_1,
            original_filename="apex_quote.pdf",
            file="quotations/apex.pdf",
            file_type="pdf",
            file_extension="pdf",
            file_size=1024,
            mime_type="application/pdf",
            uploaded_by=self.user_a,
        )
        QuotationExtraction.objects.create(
            organization=self.org_a,
            document=doc_1,
            quotation=self.quote_1,
            supplier_name="Apex Precision Engineering",
            quotation_number="APEX-QUOTE-101",
            is_approved=True,
            review_status=ReviewStatus.APPROVED,
            approved_by=self.user_a,
            approved_at=timezone.now(),
        )

        # 6. Quotation 2: Manually verified direct quotation
        self.quote_2 = Quotation.objects.create(
            organization=self.org_a,
            rfq=self.rfq,
            supplier=self.supplier_2,
            quotation_number="VANGUARD-2026",
            quotation_date=self.today - timedelta(days=1),
            validity_date=self.today + timedelta(days=45),
            currency="USD",
            subtotal=Decimal('2500.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('2500.00'),
            payment_terms="Net 60 days",
            warranty_information="36 months extended warranty",
            delivery_terms="DAP Austin",
            lead_time_weeks=Decimal('2.0'),
            status=QuotationStatus.RECEIVED,
        )
        QuotationItem.objects.create(
            quotation=self.quote_2,
            position=1,
            rfq_item_id=self.rfq_item.id,
            description="Vanguard 350bar Valve",
            quantity=Decimal('5'),
            unit="PCS",
            unit_price=Decimal('500.00'),
            line_total=Decimal('2500.00'),
            specifications={
                'Pressure': '350 bar',
                'Voltage': '24V DC',
                'Signal': '4-20mA',
            },
        )

        # 7. Quotation 3: UNREVIEWED AI extraction (pending human review)
        self.quote_3 = Quotation.objects.create(
            organization=self.org_a,
            rfq=self.rfq,
            supplier=self.supplier_3,
            quotation_number="RAW-TECH-DRAFT",
            quotation_date=self.today,
            currency="USD",
            subtotal=Decimal('1800.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('1800.00'),
            status=QuotationStatus.RECEIVED,
        )
        QuotationItem.objects.create(
            quotation=self.quote_3,
            position=1,
            rfq_item_id=self.rfq_item.id,
            description="Unreviewed Valve",
            quantity=Decimal('5'),
            unit="PCS",
            unit_price=Decimal('360.00'),
            line_total=Decimal('1800.00'),
        )
        doc_3 = QuotationDocument.objects.create(
            organization=self.org_a,
            quotation=self.quote_3,
            original_filename="raw_quote.pdf",
            file="quotations/raw.pdf",
            file_type="pdf",
            file_extension="pdf",
            file_size=1024,
            mime_type="application/pdf",
            uploaded_by=self.user_a,
        )
        QuotationExtraction.objects.create(
            organization=self.org_a,
            document=doc_3,
            quotation=self.quote_3,
            supplier_name="RawUnreviewed Tech",
            quotation_number="RAW-TECH-DRAFT",
            is_approved=False,
            review_status=ReviewStatus.UNREVIEWED,
        )

    def test_generate_and_retrieve_rfq_comparison(self):
        """Tests generating a comprehensive comparison snapshot and retrieving it via GET."""
        self.client.force_authenticate(user=self.user_a)

        # 1. Generate comparison
        gen_url = f"/api/comparisons/rfqs/{self.rfq.id}/generate/"
        response = self.client.post(gen_url, data={'approved_only': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['rfq_id'], str(self.rfq.id))
        self.assertIn('supplier_comparison', data)
        self.assertIn('price_comparison', data)
        self.assertIn('specification_matching', data)
        self.assertIn('risk_flags', data)
        self.assertIn('scoring', data)
        self.assertIn('decision_support_guardrail', data)
        self.assertFalse(data['decision_support_guardrail']['automated_purchase_enabled'])

        # Enforce approved_only check: quote 1 (approved) and quote 2 (direct) included; quote 3 (unreviewed) excluded!
        summary = data['quotations_summary']
        self.assertEqual(summary['compared_quotations_count'], 2)
        self.assertEqual(summary['unreviewed_quotations_count'], 1)
        self.assertEqual(summary['unreviewed_quotations'][0]['quotation_number'], "RAW-TECH-DRAFT")

        # 2. Retrieve comparison via GET
        get_url = f"/api/comparisons/rfqs/{self.rfq.id}/"
        get_resp = self.client.get(get_url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        get_data = get_resp.json()
        self.assertEqual(get_data['rfq_id'], str(self.rfq.id))
        self.assertEqual(len(get_data['supplier_comparison']), 2)

    def test_view_supplier_comparison_matrix(self):
        """Tests GET /api/comparisons/rfqs/<id>/suppliers/ returns side-by-side vendor cards."""
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{self.rfq.id}/suppliers/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('supplier_comparison', data)
        cards = data['supplier_comparison']
        self.assertEqual(len(cards), 2)

        # Check vendor card fields
        card1 = cards[0]
        self.assertIn('rank', card1)
        self.assertIn('supplier_name', card1)
        self.assertIn('pricing', card1)
        self.assertIn('specifications', card1)
        self.assertIn('delivery', card1)
        self.assertIn('commercial_terms', card1)
        self.assertIn('risk_profile', card1)
        self.assertIn('scoring', card1)
        self.assertIn('review_status', card1)
        self.assertTrue(card1['review_status']['is_approved'])

    def test_view_price_comparison(self):
        """Tests GET /api/comparisons/rfqs/<id>/price/ returns detailed pricing metrics and line item comparisons."""
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{self.rfq.id}/price/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('lowest_grand_total', data)
        self.assertIn('highest_grand_total', data)
        self.assertIn('max_savings_amount', data)
        self.assertIn('cherry_pick_savings', data)
        self.assertIn('quotations', data)
        self.assertIn('items_matrix', data)
        self.assertEqual(float(data['lowest_grand_total']), 2250.0)

    def test_view_specification_matching(self):
        """Tests GET /api/comparisons/rfqs/<id>/specs/ returns technical spec matching matrices."""
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{self.rfq.id}/specs/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('items', data)
        self.assertIn('supplier_summaries', data)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['item_name'], "Hydraulic Valve 350bar")

    def test_view_risk_flags(self):
        """Tests GET /api/comparisons/rfqs/<id>/risk-flags/ returns deterministic risk reports."""
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{self.rfq.id}/risk-flags/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIsInstance(data, list)
        self.assertTrue(len(data) >= 2)
        rep = data[0]
        self.assertIn('quotation_number', rep)
        self.assertIn('overall_risk_level', rep)
        self.assertIn('flags', rep)

    def test_view_scoring(self):
        """Tests GET /api/comparisons/rfqs/<id>/scoring/ returns multi-criteria scorecards and explainable formulas."""
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{self.rfq.id}/scoring/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('rankings', data)
        self.assertTrue('weights_applied' in data or 'weights_used' in data)
        self.assertTrue('scoring_limitations' in data or 'scoring_system_limitations' in data)
        rankings = data['rankings']
        self.assertEqual(len(rankings), 2)
        top = rankings[0]
        self.assertIn('final_score', top)
        self.assertIn('factors', top)
        self.assertIn('price', top['factors'])
        self.assertIn('formula_applied', top['factors']['price'])

    def test_get_and_update_scoring_weights(self):
        """Tests retrieving current weights and updating them with validation (sum == 100%)."""
        self.client.force_authenticate(user=self.user_a)

        weights_url = f"/api/comparisons/rfqs/{self.rfq.id}/weights/"

        # 1. GET weights (should be default weights)
        get_resp = self.client.get(weights_url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        w_data = get_resp.json()
        self.assertEqual(w_data['weights']['price'], 40.0)
        self.assertEqual(w_data['weights']['spec_match'], 30.0)
        self.assertFalse(w_data['is_customized'])

        # 2. PUT weights with invalid sum (totals 90% -> Bad Request)
        bad_payload = {
            'weights': {
                'price': 40.0,
                'spec_match': 30.0,
                'delivery': 10.0,
                'payment_terms': 5.0,
                'warranty': 5.0,  # Sum = 90
            }
        }
        bad_resp = self.client.put(weights_url, data=bad_payload, format='json')
        self.assertEqual(bad_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("100%", str(bad_resp.json()))

        # 3. PUT valid custom weights (e.g. Price 50%, Specs 25%, Delivery 15%, Payment 5%, Warranty 5%)
        valid_payload = {
            'weights': {
                'price': 50.0,
                'spec_match': 25.0,
                'delivery': 15.0,
                'payment_terms': 5.0,
                'warranty': 5.0,
            },
            'regenerate': True,
        }
        good_resp = self.client.put(weights_url, data=valid_payload, format='json')
        self.assertEqual(good_resp.status_code, status.HTTP_200_OK)
        updated_data = good_resp.json()
        self.assertEqual(updated_data['weights']['price'], 50.0)
        self.assertIn('comparison', updated_data)

        # 4. Verify persisted setting
        persisted_setting = RFQComparisonSetting.objects.get(rfq=self.rfq)
        self.assertEqual(persisted_setting.weights['price'], 50.0)

    def test_regenerate_comparison_endpoint(self):
        """Tests POST /api/comparisons/rfqs/<id>/regenerate/ creates a fresh snapshot."""
        self.client.force_authenticate(user=self.user_a)

        initial_count = RFQComparisonSnapshot.objects.filter(rfq=self.rfq).count()
        regen_url = f"/api/comparisons/rfqs/{self.rfq.id}/regenerate/"
        response = self.client.post(regen_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_count = RFQComparisonSnapshot.objects.filter(rfq=self.rfq).count()
        self.assertEqual(new_count, initial_count + 1)

    def test_approved_only_policy_enforcement(self):
        """
        Tests that when approved_only=False is explicitly passed, the unreviewed quotation is included,
        but its card is prominently flagged as unreviewed.
        """
        self.client.force_authenticate(user=self.user_a)

        gen_url = f"/api/comparisons/rfqs/{self.rfq.id}/generate/"
        response = self.client.post(gen_url, data={'approved_only': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # All 3 quotations should now be compared
        self.assertEqual(data['quotations_summary']['compared_quotations_count'], 3)

        # Find quote 3 in supplier cards
        cards = data['supplier_comparison']
        q3_card = next((c for c in cards if c['quotation_number'] == "RAW-TECH-DRAFT"), None)
        self.assertIsNotNone(q3_card)
        self.assertFalse(q3_card['review_status']['is_approved'])
        self.assertIn("pending human review", q3_card['review_status']['description'])

    def test_organization_tenant_isolation(self):
        """Verifies cross-tenant users (User B) cannot view or generate comparisons for Org A's RFQ."""
        self.client.force_authenticate(user=self.user_b)

        # Attempt to access Org A's RFQ comparison
        url = f"/api/comparisons/rfqs/{self.rfq.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Attempt to update weights for Org A's RFQ
        weights_url = f"/api/comparisons/rfqs/{self.rfq.id}/weights/"
        put_resp = self.client.put(weights_url, data={'weights': {'price': 50, 'spec_match': 50, 'delivery': 0, 'payment_terms': 0, 'warranty': 0}}, format='json')
        self.assertEqual(put_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        """Verifies unauthenticated requests are blocked with HTTP 401."""
        self.client.logout()
        url = f"/api/comparisons/rfqs/{self.rfq.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rfq_with_zero_quotations(self):
        """Tests that an RFQ with zero quotations handles comparison gracefully without dividing by zero."""
        empty_rfq = RFQ.objects.create(
            organization=self.org_a,
            rfq_number=f"RFQ-EMPTY-{uuid.uuid4().hex[:6].upper()}",
            title="Empty RFQ",
            currency="USD",
            created_by=self.user_a,
        )
        RFQItem.objects.create(
            rfq=empty_rfq,
            position=1,
            item_name="Pneumatic Actuator",
            quantity=Decimal('2'),
            unit="PCS",
        )
        self.client.force_authenticate(user=self.user_a)

        url = f"/api/comparisons/rfqs/{empty_rfq.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['quotations_summary']['compared_quotations_count'], 0)
        self.assertEqual(len(data['supplier_comparison']), 0)
