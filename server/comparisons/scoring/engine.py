"""
Explainable Supplier Scoring Engine for QuoteFlow AI.
Coordinates deterministic multi-criteria scoring across Price, Technical Specs, Delivery,
Payment Terms, and Warranty.
"""
from datetime import date
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from comparisons.scoring.formulas import (
    calculate_delivery_score,
    calculate_payment_score,
    calculate_price_score,
    calculate_spec_score,
    calculate_warranty_score,
)
from comparisons.scoring.schemas import (
    FactorScoreBreakdown,
    RFQSupplierScoringSummary,
    ScoringFactor,
    SupplierScoreReport,
)
from comparisons.scoring.weights import ScoringWeights, validate_weights
from comparisons.specs import SpecificationMatchingEngine

logger = logging.getLogger('quoteflow.comparisons.scoring.engine')

SCORING_SYSTEM_LIMITATIONS: List[str] = [
    "Linear Relative Price Scaling: Price competitiveness is calculated as (Lowest Price / Quoted Price) * 100. While transparent and deterministic, in low-margin procurement categories, a small percentage difference might represent significant budget impact that linear scaling treats uniformly.",
    "Unquantified Qualitative Factors: The 5 evaluation metrics (Price, Specs, Delivery, Payment, Warranty) do not measure supplier past performance, factory audit results, ESG compliance, financial insolvency risk, or communication responsiveness.",
    "Discrete Commercial Policy Tiers: Payment terms and warranty months are evaluated through standardized commercial policy bands. Bespoke contractual terms (e.g. performance bonds, stage-gate retentions, liquidated damages) may require manual buyer adjustment.",
    "Orthogonal Factor Assumption: Multi-criteria additive weighting assumes factor independence. In real-world engineering, a critical flaw in one dimension (e.g. electrical polarity mismatch) cannot be genuinely offset by an attractive price.",
    "Decision Support Only: This scoring engine is an advisory decision-support tool. It does NOT automatically award contracts, issue purchase orders, or select vendors without human procurement sign-off.",
]


class SupplierScoringEngine:
    """
    Explainable multi-criteria supplier scoring engine.
    Computes audited factor breakdowns and final rankings.
    """

    def __init__(self, default_weights: Optional[Union[ScoringWeights, Dict[str, Any]]] = None):
        self.default_weights = validate_weights(default_weights)
        self.spec_engine = SpecificationMatchingEngine()

    def score_rfq_quotations(
        self,
        rfq_or_data: Any,
        quotations_or_data: List[Any],
        weights: Optional[Union[ScoringWeights, Dict[str, Any]]] = None,
        evaluation_date: Optional[date] = None,
    ) -> RFQSupplierScoringSummary:
        """
        Evaluates and ranks all quotations submitted for an RFQ.

        Args:
            rfq_or_data: Django RFQ model instance or dictionary.
            quotations_or_data: List of Django Quotation models or list of quotation dictionaries.
            weights: Optional custom comparison weights (must total 100%).
            evaluation_date: Date used for delivery and schedule calculations (defaults to today).
        """
        eval_dt = evaluation_date or date.today()
        active_weights = validate_weights(weights) if weights is not None else self.default_weights

        rfq_info, rfq_items = self._extract_rfq_data(rfq_or_data)
        quotes_list = [self._extract_quotation_data(q) for q in quotations_or_data]

        # 1. Establish RFQ Benchmarks across all quotes
        currency = rfq_info.get('currency', 'USD')
        valid_prices = [
            Decimal(str(q['financials']['normalized_grand_total']))
            for q in quotes_list
            if q.get('financials', {}).get('normalized_grand_total') is not None
            and Decimal(str(q['financials']['normalized_grand_total'])) > Decimal('0.00')
        ]
        lowest_price = min(valid_prices) if valid_prices else None

        valid_lead_times = [
            float(q['commercial']['lead_time_weeks'])
            for q in quotes_list
            if q.get('commercial', {}).get('lead_time_weeks') is not None
            and float(q['commercial']['lead_time_weeks']) > 0
        ]
        fastest_lead_time = min(valid_lead_times) if valid_lead_times else None

        benchmarks = {
            'currency': currency,
            'lowest_price': float(lowest_price) if lowest_price else None,
            'fastest_lead_time_weeks': fastest_lead_time,
            'required_delivery_date': (
                rfq_info['required_delivery_date'].isoformat()
                if isinstance(rfq_info.get('required_delivery_date'), date)
                else str(rfq_info.get('required_delivery_date', ''))
            ),
            'target_budget': float(rfq_info.get('target_budget')) if rfq_info.get('target_budget') else None,
            'total_quotations_evaluated': len(quotes_list),
        }

        # 2. Score each quotation individually
        reports: List[SupplierScoreReport] = []
        for q_data in quotes_list:
            report = self._score_single_quotation(
                quote_data=q_data,
                rfq_info=rfq_info,
                rfq_items=rfq_items,
                benchmarks=benchmarks,
                weights=active_weights,
                evaluation_date=eval_dt,
            )
            reports.append(report)

        # 3. Sort rankings by final_score descending
        reports.sort(key=lambda r: r.final_score, reverse=True)
        for idx, report in enumerate(reports):
            report.rank = idx + 1

        return RFQSupplierScoringSummary(
            rfq_id=rfq_info.get('id'),
            rfq_number=rfq_info.get('rfq_number', 'N/A'),
            rfq_title=rfq_info.get('title', 'RFQ Evaluation'),
            weights_applied=active_weights.to_dict(),
            benchmarks=benchmarks,
            rankings=reports,
            scoring_limitations=SCORING_SYSTEM_LIMITATIONS,
        )

    def _score_single_quotation(
        self,
        quote_data: Dict[str, Any],
        rfq_info: Dict[str, Any],
        rfq_items: List[Dict[str, Any]],
        benchmarks: Dict[str, Any],
        weights: ScoringWeights,
        evaluation_date: date,
    ) -> SupplierScoreReport:
        """Computes factor breakdowns and weighted final score for a single quotation."""
        factors: Dict[str, FactorScoreBreakdown] = {}
        advisory_notes: List[str] = []

        currency = benchmarks.get('currency', 'USD')
        lowest_price = Decimal(str(benchmarks['lowest_price'])) if benchmarks.get('lowest_price') else None

        # -------------------------------------------------------------
        # Factor 1: Price Competitiveness (Default 40%)
        # -------------------------------------------------------------
        quoted_price_raw = quote_data.get('financials', {}).get('normalized_grand_total')
        quoted_price = Decimal(str(quoted_price_raw)) if quoted_price_raw is not None else None
        p_score, p_metric, p_formula, p_desc = calculate_price_score(
            quoted_price=quoted_price,
            lowest_price=lowest_price,
            currency=currency,
        )
        p_weight = weights.price
        p_weighted = (p_score * p_weight) / 100.0
        factors[ScoringFactor.PRICE.value] = FactorScoreBreakdown(
            factor=ScoringFactor.PRICE,
            name="Price Competitiveness",
            raw_value=f"{quoted_price:.2f} {currency}" if quoted_price else "N/A",
            raw_metric=p_metric,
            normalized_score=p_score,
            weight_pct=p_weight,
            weighted_score=p_weighted,
            formula_applied=p_formula,
            explanation=p_desc,
        )

        # -------------------------------------------------------------
        # Factor 2: Specification Match (Default 30%)
        # -------------------------------------------------------------
        quote_items = quote_data.get('items', [])
        spec_summary = self._evaluate_rfq_specifications(rfq_items, quote_items)
        s_score, s_metric, s_formula, s_desc = calculate_spec_score(
            spec_match_score=spec_summary['average_spec_score'],
            has_critical_mismatches=spec_summary['has_critical_mismatches'],
            mismatches_count=spec_summary['total_mismatches'],
            missing_count=spec_summary['total_missing'],
            total_requirements=spec_summary['total_requirements'],
        )
        s_weight = weights.spec_match
        s_weighted = (s_score * s_weight) / 100.0
        factors[ScoringFactor.SPEC_MATCH.value] = FactorScoreBreakdown(
            factor=ScoringFactor.SPEC_MATCH,
            name="Specification Match",
            raw_value=f"{s_score:.1f}% Compliant",
            raw_metric=s_metric,
            normalized_score=s_score,
            weight_pct=s_weight,
            weighted_score=s_weighted,
            formula_applied=s_formula,
            explanation=s_desc,
        )
        if spec_summary['has_critical_mismatches']:
            advisory_notes.append("Critical technical specification conflict detected; incompatible with RFQ requirements.")

        # -------------------------------------------------------------
        # Factor 3: Delivery Schedule (Default 15%)
        # -------------------------------------------------------------
        comm = quote_data.get('commercial', {})
        quoted_delivery_dt = comm.get('delivery_date')
        rfq_delivery_dt = rfq_info.get('required_delivery_date')
        quoted_lead_weeks = float(comm['lead_time_weeks']) if comm.get('lead_time_weeks') is not None else None
        fastest_lead_weeks = benchmarks.get('fastest_lead_time_weeks')

        d_score, d_metric, d_formula, d_desc = calculate_delivery_score(
            quoted_delivery_date=quoted_delivery_dt,
            required_delivery_date=rfq_delivery_dt,
            quoted_lead_time_weeks=quoted_lead_weeks,
            fastest_lead_time_weeks=fastest_lead_weeks,
        )
        d_weight = weights.delivery
        d_weighted = (d_score * d_weight) / 100.0
        factors[ScoringFactor.DELIVERY.value] = FactorScoreBreakdown(
            factor=ScoringFactor.DELIVERY,
            name="Delivery & Lead Time",
            raw_value=str(quoted_delivery_dt) if quoted_delivery_dt else (f"{quoted_lead_weeks:.1f} weeks" if quoted_lead_weeks else "Unstated"),
            raw_metric=d_metric,
            normalized_score=d_score,
            weight_pct=d_weight,
            weighted_score=d_weighted,
            formula_applied=d_formula,
            explanation=d_desc,
        )

        # -------------------------------------------------------------
        # Factor 4: Payment Terms (Default 10%)
        # -------------------------------------------------------------
        pay_terms = comm.get('payment_terms', '')
        pay_score, pay_metric, pay_formula, pay_desc = calculate_payment_score(payment_terms=pay_terms)
        pay_weight = weights.payment_terms
        pay_weighted = (pay_score * pay_weight) / 100.0
        factors[ScoringFactor.PAYMENT_TERMS.value] = FactorScoreBreakdown(
            factor=ScoringFactor.PAYMENT_TERMS,
            name="Commercial Payment Terms",
            raw_value=pay_terms or "Unspecified",
            raw_metric=pay_metric,
            normalized_score=pay_score,
            weight_pct=pay_weight,
            weighted_score=pay_weighted,
            formula_applied=pay_formula,
            explanation=pay_desc,
        )

        # -------------------------------------------------------------
        # Factor 5: Warranty Coverage (Default 5%)
        # -------------------------------------------------------------
        war_text = comm.get('warranty_information', '')
        w_score, w_metric, w_formula, w_desc = calculate_warranty_score(warranty_text=war_text)
        w_weight = weights.warranty
        w_weighted = (w_score * w_weight) / 100.0
        factors[ScoringFactor.WARRANTY.value] = FactorScoreBreakdown(
            factor=ScoringFactor.WARRANTY,
            name="Warranty Coverage",
            raw_value=war_text or "Unspecified",
            raw_metric=w_metric,
            normalized_score=w_score,
            weight_pct=w_weight,
            weighted_score=w_weighted,
            formula_applied=w_formula,
            explanation=w_desc,
        )

        # -------------------------------------------------------------
        # Final Score Aggregation
        # -------------------------------------------------------------
        final_score = sum(f.weighted_score for f in factors.values())
        final_score = min(100.0, max(0.0, round(final_score, 2)))

        is_recommended = not spec_summary['has_critical_mismatches'] and final_score >= 30.0
        if not is_recommended and not spec_summary['has_critical_mismatches']:
            advisory_notes.append("Final aggregate score is below 30.0; pricing or commercial terms are unfavorable.")

        return SupplierScoreReport(
            supplier_id=quote_data.get('supplier_id'),
            supplier_name=quote_data.get('supplier_name', 'Unknown Supplier'),
            quotation_id=quote_data.get('id'),
            quotation_number=quote_data.get('quotation_number', 'N/A'),
            final_score=final_score,
            factors=factors,
            is_recommended_for_consideration=is_recommended,
            advisory_notes=advisory_notes,
        )

    def _evaluate_rfq_specifications(
        self, rfq_items: List[Dict[str, Any]], quote_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Runs specification matching across all line items."""
        if not rfq_items:
            return {
                'average_spec_score': 100.0,
                'has_critical_mismatches': False,
                'total_mismatches': 0,
                'total_missing': 0,
                'total_requirements': 0,
            }

        scores: List[float] = []
        has_critical = False
        mismatches_count = 0
        missing_count = 0
        total_reqs = 0

        rfq_map: Dict[str, Dict[str, Any]] = {}
        for idx, item in enumerate(rfq_items):
            item_id = str(item.get('id', ''))
            pos = item.get('position', idx + 1)
            if item_id:
                rfq_map[item_id] = item
            rfq_map[f"pos_{pos}"] = item

        for idx, q_item in enumerate(quote_items):
            rfq_ref = str(q_item.get('rfq_item_id', ''))
            pos = q_item.get('position', idx + 1)
            matched_rfq = rfq_map.get(rfq_ref) or rfq_map.get(f"pos_{pos}")
            if not matched_rfq:
                continue

            rfq_specs = matched_rfq.get('custom_specifications') or {}
            rfq_specs = {k: v for k, v in rfq_specs.items() if str(k).lower() not in ('required_spec_summary', 'summary', 'notes', 'description')}
            quote_specs = (q_item.get('specifications') or {}).copy()

            if q_item.get('quantity') is not None and 'Quantity' not in quote_specs and 'quantity' not in quote_specs:
                quote_specs['Quantity'] = str(int(q_item.get('quantity')))

            if rfq_specs:
                summary = self.spec_engine.compare_item_specifications(
                    rfq_item_or_specs=rfq_specs,
                    supplier_item_or_specs=quote_specs,
                    item_name=q_item.get('description', f"Line #{idx+1}"),
                    use_ai=False,
                )
                scores.append(summary.spec_match_score)
                if summary.has_critical_mismatches:
                    has_critical = True
                mismatches_count += summary.mismatches_count
                missing_count += summary.missing_count
                total_reqs += summary.total_requirements_count

        avg_score = (sum(scores) / len(scores)) if scores else 100.0
        return {
            'average_spec_score': avg_score,
            'has_critical_mismatches': has_critical,
            'total_mismatches': mismatches_count,
            'total_missing': missing_count,
            'total_requirements': total_reqs,
        }

    def _extract_rfq_data(self, rfq_or_data: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extracts standard dictionary format from RFQ model or dict."""
        if isinstance(rfq_or_data, dict):
            return rfq_or_data, rfq_or_data.get('items', [])

        rfq_info = {
            'id': str(getattr(rfq_or_data, 'id', '')),
            'rfq_number': getattr(rfq_or_data, 'rfq_number', ''),
            'title': getattr(rfq_or_data, 'title', ''),
            'currency': getattr(rfq_or_data, 'currency', 'USD'),
            'required_delivery_date': getattr(rfq_or_data, 'required_delivery_date', None),
        }

        rfq_items = []
        if hasattr(rfq_or_data, 'items'):
            for r_it in rfq_or_data.items.all().order_by('position'):
                specs = {k: v for k, v in (r_it.custom_specifications or {}).items() if str(k).lower() not in ('required_spec_summary', 'summary', 'notes', 'description')}
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

        return rfq_info, rfq_items

    def _extract_quotation_data(self, quotation_or_data: Any) -> Dict[str, Any]:
        """Extracts standard dictionary format from Quotation model or dict."""
        if isinstance(quotation_or_data, dict):
            # Check if flat dictionary or structured
            data = quotation_or_data.copy()
            if 'financials' not in data:
                data['financials'] = {
                    'normalized_grand_total': data.get('total_amount') or data.get('grand_total') or data.get('price'),
                    'currency': data.get('currency', 'USD'),
                }
            if 'commercial' not in data:
                data['commercial'] = {
                    'delivery_date': data.get('delivery_date'),
                    'lead_time_weeks': data.get('lead_time_weeks'),
                    'payment_terms': data.get('payment_terms', ''),
                    'warranty_information': data.get('warranty_information', ''),
                }
            if 'items' not in data:
                data['items'] = data.get('line_items', [])
            return data

        # Django Quotation instance
        supp = getattr(quotation_or_data, 'supplier', None)
        supp_name = (
            getattr(supp, 'company_name', getattr(supp, 'name', ''))
            if supp
            else getattr(quotation_or_data, 'supplier_name', '') or 'Unknown Supplier'
        )

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
                    'line_total': q_it.line_total,
                    'specifications': q_it.specifications or {},
                })

        return {
            'id': str(getattr(quotation_or_data, 'id', '')),
            'supplier_id': str(supp.id) if supp else None,
            'supplier_name': supp_name,
            'quotation_number': getattr(quotation_or_data, 'quotation_number', 'N/A'),
            'financials': {
                'normalized_grand_total': getattr(quotation_or_data, 'total_amount', Decimal('0.00')),
                'currency': getattr(quotation_or_data, 'currency', 'USD'),
            },
            'commercial': {
                'delivery_date': getattr(quotation_or_data, 'delivery_date', None),
                'lead_time_weeks': getattr(quotation_or_data, 'lead_time_weeks', None),
                'payment_terms': getattr(quotation_or_data, 'payment_terms', ''),
                'warranty_information': getattr(quotation_or_data, 'warranty_information', ''),
            },
            'items': quote_items,
        }
