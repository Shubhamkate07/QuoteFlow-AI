"""
Integration and API endpoint tests for Quotation Normalization and Exchange Rates.
"""
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from organizations.models import Organization, OrganizationMembership, OrganizationRole
from rfqs.models import RFQ, RFQItem
from suppliers.models import Supplier
from quotations.models import Quotation, QuotationItem
from comparisons.models import ExchangeRate, NormalizedQuotationSnapshot

User = get_user_model()


class NormalizationApiTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='procurement@acme.com',
            password='TestPassword123!',
            full_name='John Buyer',
        )
        self.org = Organization.objects.create(name='Acme Aerospace', slug='acme-aero', created_by=self.user)
        self.membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        self.client.defaults['HTTP_X_ORGANIZATION_ID'] = str(self.org.id)

        self.rfq = RFQ.objects.create(
            organization=self.org,
            rfq_number='RFQ-2026-101',
            title='Turbine Components',
            currency='USD',
            created_by=self.user,
        )
        self.rfq_item = RFQItem.objects.create(
            rfq=self.rfq,
            position=1,
            item_name='Titanium Blade',
            quantity=Decimal('100.0000'),
            unit='PCS',
        )

        self.supplier = Supplier.objects.create(
            organization=self.org,
            company_name='Vanguard Castings',
        )

        self.quotation = Quotation.objects.create(
            organization=self.org,
            rfq=self.rfq,
            supplier=self.supplier,
            quotation_number='VC-900',
            currency='USD',
            payment_terms='Net 30 Days',
            lead_time_weeks=Decimal('2.0'),
            warranty_information='12 months manufacturer warranty',
            subtotal=Decimal('5000.00'),
            tax_amount=Decimal('500.00'),
            total_amount=Decimal('5500.00'),
            created_by=self.user,
        )
        self.quotation_item = QuotationItem.objects.create(
            quotation=self.quotation,
            rfq_item=self.rfq_item,
            position=1,
            description='Titanium Blade Casting',
            quantity=Decimal('100.0000'),
            unit='PCS',
            unit_price=Decimal('50.0000'),
            discount=Decimal('0.00'),
            tax=Decimal('0.00'),
        )

    def test_exchange_rate_crud_api(self):
        """Creating an exchange rate requires positive rate and source."""
        url = reverse('comparisons:exchange-rate-list')

        # 1. Reject without source
        res_fail = self.client.post(url, {
            'source_currency': 'EUR',
            'target_currency': 'USD',
            'rate': '1.085',
            'rate_source': '',
        })
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Successfully create rate
        res_create = self.client.post(url, {
            'source_currency': 'EUR',
            'target_currency': 'USD',
            'rate': '1.08500000',
            'rate_source': 'European Central Bank',
            'rate_date': '2026-11-20',
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ExchangeRate.objects.count(), 1)
        rate_obj = ExchangeRate.objects.first()
        self.assertEqual(rate_obj.source_currency, 'EUR')
        self.assertEqual(rate_obj.rate_source, 'European Central Bank')

    def test_normalize_quotation_api(self):
        """GET and POST /api/comparisons/quotations/{id}/normalize/"""
        url = reverse('comparisons:normalize-quotation', kwargs={'quotation_id': self.quotation.id})

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(data['supplier_name'], 'Vanguard Castings')
        self.assertEqual(data['commercial_terms']['payment_terms']['category'], 'NET_CREDIT')
        self.assertEqual(data['commercial_terms']['payment_terms']['credit_days'], 30)
        self.assertEqual(data['commercial_terms']['lead_time']['lead_time_weeks'], 2.0)
        self.assertEqual(data['financials']['normalized_grand_total'], 5500.0)

        # Verified that snapshot was created
        self.assertEqual(NormalizedQuotationSnapshot.objects.filter(quotation=self.quotation).count(), 1)

    def test_normalize_raw_data_api(self):
        """POST /api/comparisons/normalize-raw/ with Dozen -> PCS and INR -> USD conversion."""
        url = reverse('comparisons:normalize-raw')
        payload = {
            'extracted_data': {
                'supplier': {'supplier_name': 'Hindustan Fasteners'},
                'quotation': {'currency': 'INR', 'subtotal': 10000.0},
                'line_items': [
                    {
                        'line_number': 1,
                        'description': 'Bolts M8',
                        'quantity': 5,
                        'unit': 'DOZEN',
                        'unit_price': 2000.0,
                    }
                ],
            },
            'target_currency': 'USD',
            'exchange_rates': [
                {
                    'source_currency': 'INR',
                    'target_currency': 'USD',
                    'rate': '0.012',
                    'rate_source': 'Market Fixing',
                    'rate_date': '2026-11-20',
                }
            ],
        }

        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(data['financials']['normalized_currency'], 'USD')
        # 10,000 INR * 0.012 = $120.00 USD
        self.assertEqual(data['financials']['normalized_subtotal'], 120.0)
        # Line item: 5 dozen = 60 PCS
        item = data['items'][0]
        self.assertEqual(item['normalized_unit'], 'PCS')
        self.assertEqual(item['normalized_quantity'], 60.0)
