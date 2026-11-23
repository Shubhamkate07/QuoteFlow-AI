"""
Quotation Risk Flag Engine for QuoteFlow AI.
Coordinates deterministic risk rule evaluation across commercial, technical, and mathematical criteria.
Do not use AI to generate the underlying flags.
"""
from datetime import date
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from comparisons.risk.config import RiskEngineConfig
from comparisons.risk.evaluators import (
    evaluate_administrative_risks,
    evaluate_calculation_risks,
    evaluate_currency_risks,
    evaluate_delivery_risks,
    evaluate_payment_risks,
    evaluate_pricing_risks,
    evaluate_quantity_risks,
    evaluate_specification_risks,
    evaluate_validity_risks,
    evaluate_warranty_risks,
)
from comparisons.risk.schemas import (
    QuotationRiskReport,
    RiskFlag,
    RiskSeverity,
)

logger = logging.getLogger('quoteflow.comparisons.risk.engine')


class QuotationRiskEngine:
    """
    Core deterministic risk evaluation engine.
    Analyzes quotations against RFQ procurement benchmarks, industry norms,
    and mathematical constraints.
    """

    def __init__(self, config: Optional[RiskEngineConfig] = None):
        self.config = config or RiskEngineConfig()

    def evaluate_quotation(
        self,
        quotation_or_data: Union[Dict[str, Any], Any],
        rfq_or_data: Optional[Union[Dict[str, Any], Any]] = None,
        evaluation_date: Optional[date] = None,
    ) -> QuotationRiskReport:
        """
        Evaluates risk flags for a quotation.

        Args:
            quotation_or_data: Django Quotation instance or dictionary of extracted/normalized quotation data.
            rfq_or_data: Optional Django RFQ instance or dictionary of RFQ requirements.
            evaluation_date: Reference evaluation date (defaults to today).
        """
        eval_dt = evaluation_date or date.today()

        # 1. Normalize Quotation input data
        quote_data, quote_items = self._extract_quotation_data(quotation_or_data)

        # 2. Normalize RFQ input data
        rfq_data, rfq_items = self._extract_rfq_data(rfq_or_data, quotation_or_data)

        flags: List[RiskFlag] = []

        # 3. Execute all 10 deterministic rule evaluators
        # Commercial & Administrative
        flags.extend(evaluate_administrative_risks(quote_data, self.config))
        flags.extend(evaluate_validity_risks(quote_data, self.config, evaluation_date=eval_dt))
        flags.extend(evaluate_payment_risks(quote_data, self.config))
        flags.extend(evaluate_warranty_risks(quote_data, self.config))
        flags.extend(evaluate_currency_risks(rfq_data, quote_data, self.config))

        # Operational & Schedule
        flags.extend(evaluate_delivery_risks(rfq_data, quote_data, self.config, evaluation_date=eval_dt))
        flags.extend(evaluate_quantity_risks(rfq_items, quote_items, self.config))

        # Technical Specifications
        flags.extend(evaluate_specification_risks(rfq_items, quote_items, self.config))

        # Financial Math & Pricing
        flags.extend(evaluate_calculation_risks(quote_data, quote_items, self.config))
        flags.extend(evaluate_pricing_risks(rfq_items, quote_items, self.config))

        # 4. Tally and aggregate scoring
        critical_count = sum(1 for f in flags if f.severity == RiskSeverity.CRITICAL)
        warning_count = sum(1 for f in flags if f.severity == RiskSeverity.WARNING)
        info_count = sum(1 for f in flags if f.severity == RiskSeverity.INFO)

        # Quantitative Risk Score (0.0 to 100.0)
        # Critical flags: +30 pts each (minimum 60 if any critical exists)
        # Warning flags: +10 pts each
        # Info flags: +2 pts each
        raw_score = (critical_count * 30.0) + (warning_count * 10.0) + (info_count * 2.0)
        if critical_count > 0:
            raw_score = max(raw_score, 60.0)
        overall_score = min(raw_score, 100.0)

        # Qualitative Risk Classification
        if critical_count > 0 or overall_score >= 60.0:
            overall_level = 'CRITICAL'
        elif overall_score >= 40.0:
            overall_level = 'HIGH'
        elif overall_score >= 20.0:
            overall_level = 'MEDIUM'
        else:
            overall_level = 'LOW'

        is_acceptable = (critical_count == 0)

        quotation_id = quote_data.get('id')
        quotation_number = quote_data.get('quotation_number', 'N/A')
        supplier_name = quote_data.get('supplier_name', 'Unknown Supplier')
        rfq_id = rfq_data.get('id') if rfq_data else None

        return QuotationRiskReport(
            quotation_id=str(quotation_id) if quotation_id else None,
            quotation_number=quotation_number,
            supplier_name=supplier_name,
            rfq_id=str(rfq_id) if rfq_id else None,
            evaluation_date=eval_dt,
            overall_risk_score=overall_score,
            overall_risk_level=overall_level,
            flags=flags,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            is_acceptable=is_acceptable,
        )

    def _extract_quotation_data(
        self, quotation_or_data: Any
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extracts standard dictionary and line items from dict or Django Quotation model."""
        if isinstance(quotation_or_data, dict):
            # Check if nested extracted_data format
            data = quotation_or_data.copy()
            items = data.get('line_items') or data.get('items') or []
            return data, items

        # Django Quotation instance
        supp = getattr(quotation_or_data, 'supplier', None)
        supp_name = (
            getattr(supp, 'company_name', getattr(supp, 'name', ''))
            if supp
            else getattr(quotation_or_data, 'supplier_name', '') or ''
        )

        quote_data = {
            'id': str(getattr(quotation_or_data, 'id', '')),
            'quotation_number': getattr(quotation_or_data, 'quotation_number', ''),
            'quotation_date': getattr(quotation_or_data, 'quotation_date', None),
            'validity_date': getattr(quotation_or_data, 'validity_date', None),
            'currency': getattr(quotation_or_data, 'currency', 'USD'),
            'delivery_terms': getattr(quotation_or_data, 'delivery_terms', ''),
            'payment_terms': getattr(quotation_or_data, 'payment_terms', ''),
            'warranty_information': getattr(quotation_or_data, 'warranty_information', ''),
            'lead_time_weeks': getattr(quotation_or_data, 'lead_time_weeks', None),
            'subtotal': getattr(quotation_or_data, 'subtotal', Decimal('0.00')),
            'tax_amount': getattr(quotation_or_data, 'tax_amount', Decimal('0.00')),
            'total_amount': getattr(quotation_or_data, 'total_amount', Decimal('0.00')),
            'supplier_name': supp_name,
        }

        quote_items = []
        if hasattr(quotation_or_data, 'items'):
            for q_it in quotation_or_data.items.all():
                quote_items.append({
                    'id': str(q_it.id),
                    'rfq_item_id': str(q_it.rfq_item_id) if q_it.rfq_item_id else None,
                    'position': q_it.position,
                    'description': q_it.description,
                    'quantity': q_it.quantity,
                    'unit': q_it.unit,
                    'unit_price': q_it.unit_price,
                    'discount': q_it.discount,
                    'tax': q_it.tax,
                    'line_total': q_it.line_total,
                    'specifications': q_it.specifications or {},
                    'lead_time_days': q_it.lead_time_days,
                })

        return quote_data, quote_items

    def _extract_rfq_data(
        self, rfq_or_data: Any, quotation_or_data: Any
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extracts standard dictionary and line items from dict or Django RFQ model."""
        if rfq_or_data is None:
            # Check if linked via quotation model
            if hasattr(quotation_or_data, 'rfq') and quotation_or_data.rfq:
                rfq_or_data = quotation_or_data.rfq
            else:
                return None, []

        if isinstance(rfq_or_data, dict):
            items = rfq_or_data.get('items') or []
            return rfq_or_data, items

        # Django RFQ instance
        rfq_data = {
            'id': str(getattr(rfq_or_data, 'id', '')),
            'rfq_number': getattr(rfq_or_data, 'rfq_number', ''),
            'title': getattr(rfq_or_data, 'title', ''),
            'currency': getattr(rfq_or_data, 'currency', 'USD'),
            'required_delivery_date': getattr(rfq_or_data, 'required_delivery_date', None),
        }

        rfq_items = []
        if hasattr(rfq_or_data, 'items'):
            for r_it in rfq_or_data.items.all().order_by('position'):
                specs = r_it.custom_specifications.copy() if r_it.custom_specifications else {}
                if hasattr(r_it, 'specifications'):
                    for s in r_it.specifications.all():
                        specs[s.parameter_name] = {
                            'value': s.required_value,
                            'unit': s.tolerance_or_unit,
                            'importance': s.importance,
                        }

                rfq_items.append({
                    'id': str(r_it.id),
                    'position': r_it.position,
                    'item_name': r_it.item_name,
                    'description': r_it.description,
                    'quantity': r_it.quantity,
                    'unit': r_it.unit,
                    'target_unit_price': r_it.target_unit_price,
                    'custom_specifications': specs,
                    'required_delivery_date': r_it.effective_delivery_date,
                })

        return rfq_data, rfq_items
