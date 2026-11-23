"""
Comparison and Normalization Services.
Integrates the deterministic normalization engine with Django models and tenant organizations.
"""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from django.utils import timezone

from extractions.models import ReviewStatus
from .models import (
    ExchangeRate,
    NormalizedQuotationSnapshot,
    RFQComparisonSetting,
    RFQComparisonSnapshot,
)
from .normalization import (
    CurrencyConversionService,
    ExchangeRate as DomainExchangeRate,
    ExchangeRateTable,
    NormalizedQuotation,
    QuotationNormalizationService,
)
from .engine import PriceComparisonEngine, RFQComparisonSummary
from .scoring.weights import DEFAULT_SCORING_WEIGHTS, ScoringWeights, validate_weights


def get_org_exchange_rate_table(organization, as_of_date: Optional[date] = None) -> ExchangeRateTable:
    """
    Constructs an in-memory ExchangeRateTable from the organization's stored ExchangeRate records.
    """
    qs = ExchangeRate.objects.filter(organization=organization)
    if as_of_date:
        qs = qs.filter(rate_date__lte=as_of_date)

    table = ExchangeRateTable()
    for row in qs.order_by('-rate_date'):
        table.add_rate(
            DomainExchangeRate(
                source_currency=row.source_currency,
                target_currency=row.target_currency,
                rate=row.rate,
                rate_source=row.rate_source,
                rate_date=row.rate_date,
                notes=row.notes,
            )
        )
    return table


def normalize_quotation_for_comparison(
    quotation,
    target_currency: Optional[str] = None,
    conversion_date: Optional[date] = None,
    save_snapshot: bool = True,
    user=None,
) -> NormalizedQuotation:
    """
    Normalizes a formal Quotation model instance against its target RFQ.
    If target_currency is not provided, defaults to the RFQ's designated currency.
    If save_snapshot is True, stores a NormalizedQuotationSnapshot record.
    """
    effective_target_curr = target_currency or quotation.rfq.currency if quotation.rfq_id else quotation.currency
    rate_table = get_org_exchange_rate_table(quotation.organization, as_of_date=conversion_date or quotation.quotation_date)

    service = QuotationNormalizationService(exchange_rate_table=rate_table)
    norm = service.normalize_quotation_model(
        quotation=quotation,
        target_currency=effective_target_curr,
        conversion_date=conversion_date or quotation.quotation_date,
    )

    if save_snapshot and quotation.rfq_id:
        conv = norm.financials.currency_conversion
        NormalizedQuotationSnapshot.objects.update_or_create(
            organization=quotation.organization,
            quotation=quotation,
            rfq=quotation.rfq,
            defaults={
                'native_currency': norm.financials.native_currency,
                'normalized_currency': norm.financials.normalized_currency,
                'exchange_rate_applied': conv.exchange_rate if conv and not conv.is_identity else None,
                'rate_source': conv.rate_source if conv and not conv.is_identity else '',
                'rate_date': conv.rate_date if conv and not conv.is_identity else None,
                'normalized_data': norm.to_dict(),
                'normalized_grand_total': norm.financials.normalized_grand_total,
                'created_by': user,
            }
        )

    return norm


def normalize_extraction_for_review(
    extraction,
    target_currency: Optional[str] = None,
    rfq=None,
    rate_table: Optional[ExchangeRateTable] = None,
) -> NormalizedQuotation:
    """
    Normalizes a QuotationExtraction document before approval.
    """
    org = extraction.document.organization if extraction.document_id else None
    if not rate_table and org:
        rate_table = get_org_exchange_rate_table(org)

    service = QuotationNormalizationService(exchange_rate_table=rate_table)

    rfq_items = []
    if rfq:
        for it in rfq.items.all():
            rfq_items.append({'id': str(it.id), 'unit': it.unit})

    target_curr = target_currency or (rfq.currency if rfq else extraction.currency)

    return service.normalize(
        extracted_data=extraction.extracted_data,
        target_currency=target_curr,
        target_rfq_items=rfq_items,
        extraction_id=str(extraction.id),
        quotation_id=str(extraction.quotation_id) if extraction.quotation_id else None,
        rfq_id=str(rfq.id) if rfq else None,
    )


def is_quotation_approved_or_reviewed(quotation) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluates whether a quotation is based on approved or appropriately reviewed data.
    Distinguishes approved human-verified data from raw unreviewed AI extractions.
    """
    if quotation.status == 'rejected':
        return (
            False,
            "Quotation was officially rejected by procurement.",
            {'is_approved': False, 'review_status': 'rejected', 'source': 'quotation_status'}
        )

    if quotation.status == 'draft':
        return (
            False,
            "Quotation is an unsubmitted draft.",
            {'is_approved': False, 'review_status': 'draft', 'source': 'quotation_status'}
        )

    # Check linked AI extraction
    extractions = list(getattr(quotation, 'ai_extractions', None).all()) if hasattr(quotation, 'ai_extractions') else []
    if extractions:
        # Check if any extraction is approved
        approved_ext = next((e for e in extractions if getattr(e, 'is_approved', False) or getattr(e, 'review_status', None) == ReviewStatus.APPROVED), None)
        if approved_ext:
            rev_email = (
                getattr(getattr(approved_ext, 'approved_by', None), 'email', None) or
                getattr(getattr(approved_ext, 'reviewed_by', None), 'email', None) or
                "Authorized Reviewer"
            )
            return (
                True,
                f"Human verified and approved by {rev_email}",
                {
                    'is_approved': True,
                    'review_status': getattr(approved_ext, 'review_status', ReviewStatus.APPROVED),
                    'reviewed_by': rev_email,
                    'reviewed_at': (approved_ext.approved_at or approved_ext.reviewed_at).isoformat() if (approved_ext.approved_at or approved_ext.reviewed_at) else None,
                    'extraction_id': str(approved_ext.id),
                    'source': 'ai_extraction',
                }
            )
        else:
            latest_ext = extractions[0]
            status_disp = getattr(latest_ext, 'review_status', 'unreviewed')
            return (
                False,
                f"Quotation originated from AI extraction and is pending human review (Status: {status_disp})",
                {
                    'is_approved': False,
                    'review_status': status_disp,
                    'extraction_id': str(latest_ext.id),
                    'source': 'ai_extraction',
                }
            )

    # Direct manual entry or uploaded proposal without automated extraction
    if quotation.status in ['received', 'under_review', 'accepted']:
        return (
            True,
            "Direct quotation verified as an active commercial submission.",
            {
                'is_approved': True,
                'review_status': 'verified',
                'source': 'direct_entry',
            }
        )

    return (
        False,
        f"Quotation status ({quotation.status}) is ineligible for comparison.",
        {
            'is_approved': False,
            'review_status': quotation.status,
            'source': 'direct_entry',
        }
    )


def get_eligible_quotations_for_rfq(
    rfq,
    organization=None,
    approved_only: bool = True,
) -> Tuple[List[Any], List[Dict[str, Any]]]:
    """
    Partitions RFQ quotations into eligible comparison candidates and unreviewed/excluded entries.
    """
    org = organization or getattr(rfq, 'organization', None)
    qs = (
        rfq.quotations.filter(organization=org)
        .exclude(status='rejected')
        .select_related('supplier', 'organization')
        .prefetch_related('items', 'ai_extractions')
    )

    eligible = []
    unreviewed_or_excluded = []

    for q in qs:
        is_app, reason, meta = is_quotation_approved_or_reviewed(q)
        supp = q.supplier
        supp_name = getattr(supp, 'company_name', getattr(supp, 'name', 'Unknown Supplier')) if supp else 'Unknown Supplier'

        entry_info = {
            'quotation_id': str(q.id),
            'quotation_number': q.quotation_number,
            'supplier_id': str(supp.id) if supp else None,
            'supplier_name': supp_name,
            'status': q.status,
            'is_approved': is_app,
            'reason': reason,
            'review_metadata': meta,
        }

        if approved_only:
            if is_app:
                eligible.append(q)
            else:
                unreviewed_or_excluded.append(entry_info)
        else:
            eligible.append(q)
            if not is_app:
                unreviewed_or_excluded.append(entry_info)

    return eligible, unreviewed_or_excluded


def compare_rfq_quotations(
    rfq,
    comparison_currency: Optional[str] = None,
    conversion_date: Optional[date] = None,
    save_snapshot: bool = True,
    user=None,
    organization=None,
    include_incompatible: bool = False,
    approved_only: bool = True,
) -> RFQComparisonSummary:
    """
    Executes deterministic price comparison across all vendor quotations for an RFQ.
    1. Loads received/reviewed/completed quotations for the RFQ.
    2. Builds the organization's corporate exchange rate table.
    3. Runs PriceComparisonEngine.
    4. Optionally persists an RFQComparisonSnapshot record for historical audit and fast retrieval.
    """
    org = organization or getattr(rfq, 'organization', None)

    # 1. Fetch eligible quotations for RFQ
    quotations, _ = get_eligible_quotations_for_rfq(
        rfq=rfq,
        organization=org,
        approved_only=approved_only,
    )

    # 2. Build exchange rate table
    rate_table = get_org_exchange_rate_table(org, as_of_date=conversion_date)

    # 3. Execute deterministic comparison engine
    engine = PriceComparisonEngine(
        rfq=rfq,
        quotations=quotations,
        comparison_currency=comparison_currency,
        exchange_rate_table=rate_table,
        conversion_date=conversion_date,
        include_incompatible_in_lowest=include_incompatible,
    )
    summary = engine.compare()

    # 4. Persist snapshot if requested
    if save_snapshot and org:
        RFQComparisonSnapshot.objects.create(
            organization=org,
            rfq=rfq,
            comparison_currency=summary.comparison_currency,
            quotations_count=summary.quotations_compared_count,
            lowest_grand_total=summary.lowest_grand_total,
            highest_grand_total=summary.highest_grand_total,
            potential_savings=summary.max_savings_amount,
            cherry_pick_total=summary.cherry_pick_total,
            cherry_pick_savings=summary.cherry_pick_savings,
            summary_data=summary.to_dict(),
            created_by=user,
        )

    return summary


def get_latest_rfq_comparison(rfq, organization=None) -> Optional[RFQComparisonSnapshot]:
    """
    Retrieves the most recent RFQComparisonSnapshot for an RFQ if available.
    """
    org = organization or getattr(rfq, 'organization', None)
    return RFQComparisonSnapshot.objects.filter(
        organization=org,
        rfq=rfq,
    ).order_by('-created_at').first()


def match_specifications_for_items(
    rfq_item,
    quotation_item,
    use_ai: bool = False,
):
    """
    Executes specification matching between a single RFQItem and QuotationItem.
    """
    from .specs import SpecificationMatchingEngine
    engine = SpecificationMatchingEngine()
    return engine.compare_item_specifications(
        rfq_item_or_specs=rfq_item,
        supplier_item_or_specs=quotation_item,
        item_name=getattr(rfq_item, 'item_name', 'Line Item'),
        use_ai=use_ai,
    )


def compare_rfq_specifications(
    rfq,
    organization=None,
    use_ai: bool = False,
    quotations: Optional[List[Any]] = None,
    approved_only: bool = True,
) -> Dict[str, Any]:
    """
    Executes full specification matching across all line items and supplier quotations for an RFQ.
    Returns:
    {
        'rfq_id': str,
        'rfq_number': str,
        'rfq_title': str,
        'items': [
            {
                'rfq_item_id': str,
                'item_name': str,
                'position': int,
                'supplier_evaluations': [ItemSpecMatchSummary.to_dict()]
            }
        ],
        'supplier_summaries': [
            {
                'supplier_id': str,
                'supplier_name': str,
                'average_score': float,
                'overall_verdict': str,
                'total_critical_mismatches': int
            }
        ]
    }
    """
    from .specs import SpecificationMatchingEngine, SpecVerdict
    org = organization or getattr(rfq, 'organization', None)
    engine = SpecificationMatchingEngine()

    rfq_items = list(rfq.items.all().order_by('position'))
    if quotations is None:
        quotations, _ = get_eligible_quotations_for_rfq(
            rfq=rfq,
            organization=org,
            approved_only=approved_only,
        )

    items_results = []
    supplier_scores: Dict[str, Dict[str, Any]] = {}

    for q in quotations:
        supp = q.supplier
        supp_id = str(supp.id) if supp else f"sup_{str(q.id)[:8]}"
        supp_name = getattr(supp, 'company_name', getattr(supp, 'name', getattr(q, 'supplier_name', 'Unknown Supplier')))
        if supp_id not in supplier_scores:
            supplier_scores[supp_id] = {
                'supplier_id': supp_id,
                'supplier_name': supp_name,
                'quotation_id': str(q.id),
                'scores': [],
                'critical_mismatches': 0,
                'verdicts': [],
            }

    for rfq_item in rfq_items:
        supplier_evals = []
        for q in quotations:
            supp = q.supplier
            supp_id = str(supp.id) if supp else f"sup_{str(q.id)[:8]}"

            # Find matching line item
            matching_q_item = None
            for qi in q.items.all():
                if qi.rfq_item_id and str(qi.rfq_item_id) == str(rfq_item.id):
                    matching_q_item = qi
                    break
                elif qi.position == rfq_item.position:
                    matching_q_item = qi
                    break

            if matching_q_item:
                summary = engine.compare_item_specifications(
                    rfq_item_or_specs=rfq_item,
                    supplier_item_or_specs=matching_q_item,
                    item_name=rfq_item.item_name,
                    rfq_item_id=str(rfq_item.id),
                    quotation_item_id=str(matching_q_item.id),
                    supplier_id=supp_id,
                    supplier_name=supplier_scores[supp_id]['supplier_name'],
                    use_ai=use_ai,
                )
                supplier_evals.append(summary.to_dict())
                supplier_scores[supp_id]['scores'].append(summary.spec_match_score)
                if summary.has_critical_mismatches:
                    supplier_scores[supp_id]['critical_mismatches'] += 1
                supplier_scores[supp_id]['verdicts'].append(summary.verdict)

        items_results.append({
            'rfq_item_id': str(rfq_item.id),
            'item_name': rfq_item.item_name,
            'position': rfq_item.position,
            'supplier_evaluations': supplier_evals,
        })

    # Compile overall supplier compliance summaries
    supplier_summaries = []
    for s_id, s_info in supplier_scores.items():
        scores = s_info['scores']
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        verdicts = s_info['verdicts']

        if s_info['critical_mismatches'] > 0 or any(v == SpecVerdict.NON_COMPLIANT for v in verdicts):
            overall_verdict = SpecVerdict.NON_COMPLIANT.value
        elif any(v == SpecVerdict.INCOMPLETE for v in verdicts):
            overall_verdict = SpecVerdict.INCOMPLETE.value
        elif any(v == SpecVerdict.SPEC_VARIANCE for v in verdicts) or avg_score < 100.0:
            overall_verdict = SpecVerdict.SPEC_VARIANCE.value
        else:
            overall_verdict = SpecVerdict.COMPLIANT.value

        supplier_summaries.append({
            'supplier_id': s_id,
            'supplier_name': s_info['supplier_name'],
            'quotation_id': s_info['quotation_id'],
            'average_score': avg_score,
            'overall_verdict': overall_verdict,
            'total_critical_mismatches': s_info['critical_mismatches'],
        })

    return {
        'rfq_id': str(rfq.id),
        'rfq_number': getattr(rfq, 'rfq_number', ''),
        'rfq_title': getattr(rfq, 'title', ''),
        'items': items_results,
        'supplier_summaries': supplier_summaries,
    }


def evaluate_quotation_risk_report(
    quotation,
    rfq=None,
    config=None,
    evaluation_date: Optional[date] = None,
):
    """
    Evaluates commercial, technical, and mathematical risk flags for an individual Quotation.
    """
    from .risk import QuotationRiskEngine, RiskEngineConfig
    engine = QuotationRiskEngine(config=config or RiskEngineConfig())
    return engine.evaluate_quotation(
        quotation_or_data=quotation,
        rfq_or_data=rfq,
        evaluation_date=evaluation_date,
    )


def evaluate_rfq_quotations_risk_reports(
    rfq,
    organization=None,
    config=None,
    evaluation_date: Optional[date] = None,
    quotations: Optional[List[Any]] = None,
    approved_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Evaluates risk reports across all active quotations for an RFQ.
    """
    from .risk import QuotationRiskEngine, RiskEngineConfig
    org = organization or getattr(rfq, 'organization', None)
    engine = QuotationRiskEngine(config=config or RiskEngineConfig())

    if quotations is None:
        quotations, _ = get_eligible_quotations_for_rfq(
            rfq=rfq,
            organization=org,
            approved_only=approved_only,
        )

    reports = []
    for q in quotations:
        rep = engine.evaluate_quotation(
            quotation_or_data=q,
            rfq_or_data=rfq,
            evaluation_date=evaluation_date,
        )
        reports.append(rep.to_dict())

    return reports


def score_rfq_quotations(
    rfq,
    weights=None,
    organization=None,
    evaluation_date: Optional[date] = None,
    quotations_or_data: Optional[List[Any]] = None,
    approved_only: bool = True,
):
    """
    Evaluates explainable multi-criteria supplier scoring across all quotations for an RFQ.
    """
    from .scoring import SupplierScoringEngine
    org = organization or getattr(rfq, 'organization', None)

    if quotations_or_data is None:
        quotations_or_data, _ = get_eligible_quotations_for_rfq(
            rfq=rfq,
            organization=org,
            approved_only=approved_only,
        )

    engine = SupplierScoringEngine()
    return engine.score_rfq_quotations(
        rfq_or_data=rfq,
        quotations_or_data=quotations_or_data,
        weights=weights,
        evaluation_date=evaluation_date,
    )


def get_or_create_rfq_comparison_setting(rfq, organization=None) -> RFQComparisonSetting:
    """Retrieves or initializes the RFQComparisonSetting record for an RFQ."""
    org = organization or getattr(rfq, 'organization', None)
    setting, _ = RFQComparisonSetting.objects.get_or_create(
        organization=org,
        rfq=rfq,
        defaults={
            'weights': DEFAULT_SCORING_WEIGHTS.to_dict(),
            'comparison_currency': getattr(rfq, 'currency', 'USD') or 'USD',
            'approved_only': True,
            'include_incompatible': False,
        }
    )
    if not setting.weights:
        setting.weights = DEFAULT_SCORING_WEIGHTS.to_dict()
        setting.save(update_fields=['weights', 'updated_at'])
    return setting


def update_rfq_comparison_setting(
    rfq,
    weights: Optional[Dict[str, Any]] = None,
    comparison_currency: Optional[str] = None,
    approved_only: Optional[bool] = None,
    include_incompatible: Optional[bool] = None,
    user=None,
    organization=None,
) -> RFQComparisonSetting:
    """Updates and validates comparison preferences and scoring weights for an RFQ."""
    setting = get_or_create_rfq_comparison_setting(rfq, organization=organization)
    update_fields = ['updated_at']

    if weights is not None:
        validated_weights = validate_weights(weights)
        setting.weights = validated_weights.to_dict()
        update_fields.append('weights')

    if comparison_currency is not None:
        setting.comparison_currency = comparison_currency.strip().upper()
        update_fields.append('comparison_currency')

    if approved_only is not None:
        setting.approved_only = bool(approved_only)
        update_fields.append('approved_only')

    if include_incompatible is not None:
        setting.include_incompatible = bool(include_incompatible)
        update_fields.append('include_incompatible')

    if user:
        setting.updated_by = user
        update_fields.append('updated_by')

    setting.save(update_fields=update_fields)
    return setting


def build_supplier_comparison_matrix(
    eligible_quotations: List[Any],
    price_summary: Any,
    specs_summary: Dict[str, Any],
    risk_reports: List[Dict[str, Any]],
    scoring_summary: Any,
) -> List[Dict[str, Any]]:
    """
    Synthesizes price, specifications, risk, delivery, commercial terms, and scoring
    into a unified side-by-side vendor matrix.
    """
    # Build lookup maps by quotation_id
    price_by_quote_id = {}
    price_dict = price_summary.to_dict() if hasattr(price_summary, 'to_dict') else price_summary
    for q_dict in price_dict.get('quotations', []):
        price_by_quote_id[str(q_dict.get('quotation_id'))] = q_dict

    specs_by_quote_id = {}
    for s_sum in specs_summary.get('supplier_summaries', []):
        specs_by_quote_id[str(s_sum.get('quotation_id'))] = s_sum

    risk_by_quote_id = {}
    for r_rep in risk_reports:
        risk_by_quote_id[str(r_rep.get('quotation_id'))] = r_rep

    score_by_quote_id = {}
    scoring_dict = scoring_summary.to_dict() if hasattr(scoring_summary, 'to_dict') else scoring_summary
    for rank_idx, report in enumerate(scoring_dict.get('rankings', []), start=1):
        q_id = str(report.get('quotation_id'))
        score_by_quote_id[q_id] = (rank_idx, report)

    cards = []
    for q in eligible_quotations:
        q_id = str(q.id)
        supp = q.supplier
        supp_id = str(supp.id) if supp else f"sup_{q_id[:8]}"
        supp_name = getattr(supp, 'company_name', getattr(supp, 'name', getattr(q, 'supplier_name', 'Unknown Supplier')))

        is_app, rev_desc, rev_meta = is_quotation_approved_or_reviewed(q)
        price_info = price_by_quote_id.get(q_id, {})
        spec_info = specs_by_quote_id.get(q_id, {})
        risk_info = risk_by_quote_id.get(q_id, {})
        score_tuple = score_by_quote_id.get(q_id)
        rank_idx = score_tuple[0] if score_tuple else None
        score_info = score_tuple[1] if score_tuple else {}

        # Commercial details
        comm_del = getattr(q, 'delivery_terms', '')
        comm_pay = getattr(q, 'payment_terms', '') or 'Standard Trade Credit'
        comm_war = getattr(q, 'warranty_information', '') or 'Standard Warranty'
        lead_weeks = float(q.lead_time_weeks) if getattr(q, 'lead_time_weeks', None) is not None else None

        cards.append({
            'rank': rank_idx,
            'supplier_id': supp_id,
            'supplier_name': supp_name,
            'quotation_id': q_id,
            'quotation_number': q.quotation_number,
            'review_status': {
                'is_approved': is_app,
                'description': rev_desc,
                'metadata': rev_meta,
            },
            'pricing': {
                'currency': price_info.get('currency', getattr(q, 'currency', 'USD')),
                'subtotal': price_info.get('subtotal'),
                'tax_amount': price_info.get('tax_amount'),
                'shipping_amount': price_info.get('shipping_amount'),
                'discount_amount': price_info.get('discount_amount'),
                'grand_total': price_info.get('grand_total', float(q.total_amount)),
                'price_difference_from_lowest': price_info.get('price_difference_from_lowest'),
                'percentage_difference_from_lowest': price_info.get('percentage_difference_from_lowest'),
                'is_lowest_price': price_info.get('is_lowest_price', False),
            },
            'specifications': {
                'compliance_score': spec_info.get('average_score', 100.0),
                'overall_verdict': spec_info.get('overall_verdict', 'Compliant'),
                'total_critical_mismatches': spec_info.get('total_critical_mismatches', 0),
            },
            'delivery': {
                'delivery_terms': comm_del,
                'lead_time_weeks': lead_weeks,
                'on_time_status': 'On Schedule' if (not risk_info or not any(f.get('type') == 'delivery_delay' for f in risk_info.get('flags', []))) else 'Delayed',
            },
            'commercial_terms': {
                'payment_terms': comm_pay,
                'warranty_information': comm_war,
            },
            'risk_profile': {
                'total_flags_count': len(risk_info.get('flags', [])) if risk_info else 0,
                'high_severity_count': risk_info.get('high_severity_count', 0) if risk_info else 0,
                'overall_risk_level': risk_info.get('overall_risk_level', 'LOW') if risk_info else 'LOW',
            },
            'scoring': {
                'final_score': score_info.get('final_score'),
                'is_recommended_for_consideration': score_info.get('is_recommended_for_consideration', True),
                'advisory_notes': score_info.get('advisory_notes', []),
                'factors': score_info.get('factors', {}),
            },
        })

    # Sort cards by rank (lowest rank number first; unranked last)
    cards.sort(key=lambda c: (c['rank'] is None, c['rank'] or 999))
    return cards


def generate_comprehensive_rfq_comparison(
    rfq,
    weights: Optional[Dict[str, Any]] = None,
    comparison_currency: Optional[str] = None,
    conversion_date: Optional[date] = None,
    approved_only: Optional[bool] = None,
    include_incompatible: Optional[bool] = None,
    save_snapshot: bool = True,
    user=None,
    organization=None,
) -> Dict[str, Any]:
    """
    Generates a unified, comprehensive comparison run across all dimensions:
    - Price Comparison
    - Specification Matching
    - Risk Flags
    - Explainable Supplier Scoring
    - Side-by-Side Supplier Comparison Matrix
    Enforces that comparison results are based strictly on approved/reviewed quotation data.
    """
    from .risk import QuotationRiskEngine, RiskEngineConfig
    from .scoring import SupplierScoringEngine, SCORING_SYSTEM_LIMITATIONS

    org = organization or getattr(rfq, 'organization', None)

    # 1. Resolve active settings & weights
    setting = get_or_create_rfq_comparison_setting(rfq, organization=org)
    active_weights = validate_weights(weights or setting.weights)
    target_currency = (comparison_currency or setting.comparison_currency or getattr(rfq, 'currency', 'USD') or 'USD').strip().upper()
    filter_approved_only = approved_only if approved_only is not None else setting.approved_only
    allow_incompatible = include_incompatible if include_incompatible is not None else setting.include_incompatible

    if hasattr(rfq, 'items') and not rfq.items.exists():
        empty_price = {
            'rfq_id': str(rfq.id),
            'rfq_number': getattr(rfq, 'rfq_number', ''),
            'rfq_title': getattr(rfq, 'title', ''),
            'comparison_currency': target_currency,
            'quotations_compared_count': 0,
            'lowest_grand_total': None,
            'highest_grand_total': None,
            'max_savings_amount': 0.0,
            'max_savings_percentage': 0.0,
            'cherry_pick_total': 0.0,
            'cherry_pick_savings': 0.0,
            'items_matrix': [],
            'quotations': [],
            'warnings': ['RFQ has no line items defined.'],
        }
        return {
            'rfq_id': str(rfq.id),
            'rfq_number': getattr(rfq, 'rfq_number', ''),
            'rfq_title': getattr(rfq, 'title', ''),
            'comparison_currency': target_currency,
            'generated_at': timezone.now().isoformat(),
            'settings': {
                'approved_only': filter_approved_only,
                'include_incompatible': allow_incompatible,
                'weights': active_weights.to_dict(),
            },
            'quotations_summary': {
                'total_active_quotations': 0,
                'compared_quotations_count': 0,
                'unreviewed_quotations_count': 0,
                'unreviewed_quotations': [],
            },
            'supplier_comparison': [],
            'price_comparison': empty_price,
            'specification_matching': {
                'rfq_id': str(rfq.id),
                'rfq_number': getattr(rfq, 'rfq_number', ''),
                'rfq_title': getattr(rfq, 'title', ''),
                'items': [],
                'supplier_summaries': [],
            },
            'risk_flags': [],
            'scoring': {
                'rfq_id': str(rfq.id),
                'rfq_number': getattr(rfq, 'rfq_number', ''),
                'weights_applied': active_weights.to_dict(),
                'rankings': [],
                'scoring_limitations': SCORING_SYSTEM_LIMITATIONS,
                'disclaimer': 'Decision-support only.',
            },
            'decision_support_guardrail': {
                'automated_purchase_enabled': False,
                'statement': 'Scoring rankings and comparison results are decision-support guidelines only.',
            },
            'scoring_system_limitations': SCORING_SYSTEM_LIMITATIONS,
        }

    # 2. Filter eligible quotations (approved vs unreviewed)
    eligible_quotations, unreviewed_list = get_eligible_quotations_for_rfq(
        rfq=rfq,
        organization=org,
        approved_only=filter_approved_only,
    )

    rate_table = get_org_exchange_rate_table(org, as_of_date=conversion_date)

    # 3. Price Comparison Engine
    price_engine = PriceComparisonEngine(
        rfq=rfq,
        quotations=eligible_quotations,
        comparison_currency=target_currency,
        exchange_rate_table=rate_table,
        conversion_date=conversion_date,
        include_incompatible_in_lowest=allow_incompatible,
    )
    price_summary = price_engine.compare()

    # 4. Specification Matching Engine
    specs_result = compare_rfq_specifications(
        rfq=rfq,
        organization=org,
        quotations=eligible_quotations,
        approved_only=filter_approved_only,
    )

    # 5. Risk Flags Engine
    risk_engine = QuotationRiskEngine(config=RiskEngineConfig())
    risk_reports = [
        risk_engine.evaluate_quotation(quotation_or_data=q, rfq_or_data=rfq, evaluation_date=conversion_date).to_dict()
        for q in eligible_quotations
    ]

    # 6. Explainable Supplier Scoring Engine
    scoring_engine = SupplierScoringEngine()
    scoring_summary = scoring_engine.score_rfq_quotations(
        rfq_or_data=rfq,
        quotations_or_data=eligible_quotations,
        weights=active_weights,
        evaluation_date=conversion_date,
    )

    # 7. Side-by-Side Supplier Matrix
    supplier_cards = build_supplier_comparison_matrix(
        eligible_quotations=eligible_quotations,
        price_summary=price_summary,
        specs_summary=specs_result,
        risk_reports=risk_reports,
        scoring_summary=scoring_summary,
    )

    # 8. Assemble Comprehensive Comparison Result
    price_dict = price_summary.to_dict()
    result = {
        'rfq_id': str(rfq.id),
        'rfq_number': getattr(rfq, 'rfq_number', ''),
        'rfq_title': getattr(rfq, 'title', ''),
        'comparison_currency': target_currency,
        'generated_at': timezone.now().isoformat(),
        'quotations_compared_count': price_summary.quotations_compared_count,
        'lowest_grand_total': float(price_summary.lowest_grand_total) if price_summary.lowest_grand_total is not None else None,
        'highest_grand_total': float(price_summary.highest_grand_total) if price_summary.highest_grand_total is not None else None,
        'items_matrix': price_dict.get('items_matrix', []),
        'quotations': price_dict.get('quotations', []),
        'potential_savings': float(price_summary.max_savings_amount),
        'cherry_pick_total': float(price_summary.cherry_pick_total),
        'cherry_pick_savings': float(price_summary.cherry_pick_savings),
        'settings': {
            'approved_only': filter_approved_only,
            'include_incompatible': allow_incompatible,
            'weights': active_weights.to_dict(),
        },
        'quotations_summary': {
            'total_active_quotations': len(eligible_quotations) + len(unreviewed_list),
            'compared_quotations_count': len(eligible_quotations),
            'unreviewed_quotations_count': len(unreviewed_list),
            'unreviewed_quotations': unreviewed_list,
        },
        'supplier_comparison': supplier_cards,
        'price_comparison': price_summary.to_dict(),
        'specification_matching': specs_result,
        'risk_flags': risk_reports,
        'scoring': scoring_summary.to_dict(),
        'decision_support_guardrail': {
            'automated_purchase_enabled': False,
            'statement': (
                "Scoring rankings and comparison results are decision-support guidelines only. "
                "The system does not execute automated purchasing or supplier awards without authorized procurement approval."
            ),
        },
        'scoring_system_limitations': SCORING_SYSTEM_LIMITATIONS,
    }

    # 9. Persist Snapshot
    if save_snapshot and org:
        RFQComparisonSnapshot.objects.create(
            organization=org,
            rfq=rfq,
            comparison_currency=target_currency,
            quotations_count=len(eligible_quotations),
            lowest_grand_total=price_summary.lowest_grand_total,
            highest_grand_total=price_summary.highest_grand_total,
            potential_savings=price_summary.max_savings_amount,
            cherry_pick_total=price_summary.cherry_pick_total,
            cherry_pick_savings=price_summary.cherry_pick_savings,
            weights_used=active_weights.to_dict(),
            approved_only_applied=filter_approved_only,
            unreviewed_quotations_count=len(unreviewed_list),
            summary_data=result,
            created_by=user,
        )

    return result


def get_or_generate_comprehensive_comparison(
    rfq,
    organization=None,
    force_refresh: bool = False,
    user=None,
    approved_only: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Returns latest cached snapshot or automatically executes comparison if none exists or force_refresh is True.
    """
    org = organization or getattr(rfq, 'organization', None)
    if not force_refresh:
        latest = get_latest_rfq_comparison(rfq=rfq, organization=org)
        if latest and latest.summary_data and 'supplier_comparison' in latest.summary_data:
            snapshot_approved_only = latest.summary_data.get('settings', {}).get('approved_only')
            if approved_only is None or snapshot_approved_only == approved_only:
                return latest.summary_data

    return generate_comprehensive_rfq_comparison(
        rfq=rfq,
        approved_only=approved_only,
        save_snapshot=True,
        user=user,
        organization=org,
    )





