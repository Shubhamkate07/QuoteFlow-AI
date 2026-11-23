"""
Deterministic Price Comparison Engine for QuoteFlow AI.
Performs apples-to-apples price comparison, line-item ranking, financial reconciliation,
currency normalization, and cherry-pick (split-award) optimization across competing quotations.
Strictly relies on deterministic Python arithmetic; does not use AI for calculations.
"""
from datetime import date
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional

from .formulas import (
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
from .schemas import (
    CalculationInconsistency,
    ItemCompatibilityStatus,
    LineItemComparisonResult,
    QuotationComparisonResult,
    RFQComparisonSummary,
    SupplierItemBid,
)
from .validator import ComparisonValidator, ComparisonValidationError
from ..normalization import (
    ExchangeRateTable,
    InvalidCurrencyCodeError,
    MissingExchangeRateError,
    NormalizedQuotation,
    QuotationNormalizationService,
)

logger = logging.getLogger('quoteflow.comparisons.engine')


class PriceComparisonEngine:
    """
    Core deterministic price comparison engine for RFQs.
    Compares all quotations submitted for an RFQ on a single, normalized financial basis.
    """

    def __init__(
        self,
        rfq,
        quotations: List[Any],
        comparison_currency: Optional[str] = None,
        exchange_rate_table: Optional[ExchangeRateTable] = None,
        conversion_date: Optional[date] = None,
        include_incompatible_in_lowest: bool = False,
    ):
        self.rfq = rfq
        self.raw_quotations = quotations
        self.comparison_currency = (
            comparison_currency or getattr(rfq, 'currency', 'USD') or 'USD'
        ).strip().upper()
        self.exchange_rate_table = exchange_rate_table or ExchangeRateTable()
        self.conversion_date = conversion_date
        self.include_incompatible_in_lowest = include_incompatible_in_lowest

        self.normalization_service = QuotationNormalizationService(
            exchange_rate_table=self.exchange_rate_table
        )
        self.warnings: List[str] = []

    def compare(self) -> RFQComparisonSummary:
        """
        Executes the full deterministic comparison pipeline.
        Returns a complete, serializable RFQComparisonSummary.
        """
        # 1. Validation & Isolation Checks
        rfq_warnings = ComparisonValidator.validate_rfq_for_comparison(self.rfq)
        self.warnings.extend(rfq_warnings)
        ComparisonValidator.validate_tenant_isolation(self.rfq, self.raw_quotations)

        # Retrieve RFQ Items
        rfq_items = list(
            self.rfq.items.all().order_by('position')
            if hasattr(self.rfq, 'items')
            else getattr(self.rfq, 'rfq_items', [])
        )
        total_rfq_items_count = len(rfq_items)

        # 2. Normalize Each Quotation to the Comparison Currency and RFQ Units
        normalized_quotes_map: Dict[str, Optional[NormalizedQuotation]] = {}
        quote_currency_errors: Dict[str, str] = {}

        for quote in self.raw_quotations:
            quote_id = str(quote.id)
            try:
                norm = self.normalization_service.normalize_quotation_model(
                    quotation=quote,
                    target_currency=self.comparison_currency,
                    conversion_date=self.conversion_date or getattr(quote, 'quotation_date', None),
                )
                normalized_quotes_map[quote_id] = norm
                if norm and norm.warnings:
                    self.warnings.extend(norm.warnings)
                if norm and norm.financials.normalized_currency != self.comparison_currency:
                    self.warnings.append(
                        f"Quotation {getattr(quote, 'quotation_number', quote_id)} (Currency: {quote.currency}) "
                        f"cannot be converted to {self.comparison_currency}: No exchange rate found in corporate exchange rates."
                    )
            except (MissingExchangeRateError, InvalidCurrencyCodeError, ValueError) as curr_err:
                msg = (
                    f"Quotation {getattr(quote, 'quotation_number', quote_id)} (Currency: {quote.currency}) "
                    f"cannot be converted to {self.comparison_currency}: {str(curr_err)}"
                )
                logger.warning(msg)
                self.warnings.append(msg)
                normalized_quotes_map[quote_id] = None
                quote_currency_errors[quote_id] = str(curr_err)

        # 3. Line-Item Comparison Matrix
        items_matrix: List[LineItemComparisonResult] = []
        # Index RFQ items by ID and position for quick lookup
        rfq_item_id_map = {str(item.id): item for item in rfq_items}

        for rfq_item in rfq_items:
            item_result = self._compare_single_rfq_item(
                rfq_item=rfq_item,
                normalized_quotes_map=normalized_quotes_map,
                quote_currency_errors=quote_currency_errors,
            )
            items_matrix.append(item_result)

        # 4. Quotation-Level Financial Reconciliation & Ranking
        quotations_results: List[QuotationComparisonResult] = []
        for quote in self.raw_quotations:
            quote_id = str(quote.id)
            norm = normalized_quotes_map.get(quote_id)
            curr_error = quote_currency_errors.get(quote_id)

            q_result = self._reconcile_quotation_comparison(
                quote=quote,
                norm=norm,
                items_matrix=items_matrix,
                total_rfq_items_count=total_rfq_items_count,
                currency_error=curr_error,
            )
            quotations_results.append(q_result)

        # 5. Global Financial Benchmarks & Quotation Ranking
        self._rank_and_benchmark_quotations(quotations_results)

        # 6. Cherry-Pick (Split-Award) Analysis
        cherry_pick_total = Decimal('0.00')
        for item_res in items_matrix:
            if item_res.lowest_extended_price is not None:
                cherry_pick_total += item_res.lowest_extended_price
        cherry_pick_total = quantize_currency(cherry_pick_total)

        # Lowest single vendor total
        comparable_quotes = [q for q in quotations_results if q.is_comparable and q.is_full_coverage]
        lowest_grand_total = (
            min((q.grand_total for q in comparable_quotes), default=None)
            if comparable_quotes
            else (min((q.grand_total for q in quotations_results if q.is_comparable), default=None))
        )

        cherry_pick_savings = Decimal('0.00')
        cherry_pick_savings_pct = Decimal('0.00')
        if lowest_grand_total and lowest_grand_total > cherry_pick_total:
            cherry_pick_savings = quantize_currency(lowest_grand_total - cherry_pick_total)
            cherry_pick_savings_pct = calculate_savings_percentage(lowest_grand_total, cherry_pick_total)

        # Overall summary stats
        valid_totals = [q.grand_total for q in quotations_results if q.is_comparable]
        highest_grand_total = max(valid_totals) if valid_totals else None
        average_grand_total = (
            quantize_currency(sum(valid_totals) / Decimal(len(valid_totals)))
            if valid_totals
            else None
        )
        median_grand_total = self._calculate_median(valid_totals) if valid_totals else None

        # Best Quote Identifiers
        lowest_quote = next((q for q in quotations_results if q.grand_total == lowest_grand_total), None) if lowest_grand_total else None
        highest_quote = next((q for q in quotations_results if q.grand_total == highest_grand_total), None) if highest_grand_total else None

        max_savings_amount = Decimal('0.00')
        max_savings_pct = Decimal('0.00')
        if lowest_grand_total and highest_grand_total:
            max_savings_amount = quantize_currency(highest_grand_total - lowest_grand_total)
            max_savings_pct = calculate_savings_percentage(highest_grand_total, lowest_grand_total)

        return RFQComparisonSummary(
            rfq_id=str(self.rfq.id),
            rfq_number=getattr(self.rfq, 'rfq_number', ''),
            rfq_title=getattr(self.rfq, 'title', ''),
            comparison_currency=self.comparison_currency,
            quotations_compared_count=len(self.raw_quotations),
            lowest_grand_total=lowest_grand_total,
            lowest_quote_id=lowest_quote.quotation_id if lowest_quote else None,
            lowest_supplier_name=lowest_quote.supplier_name if lowest_quote else None,
            highest_grand_total=highest_grand_total,
            highest_supplier_name=highest_quote.supplier_name if highest_quote else None,
            average_grand_total=average_grand_total,
            median_grand_total=median_grand_total,
            max_savings_amount=max_savings_amount,
            max_savings_percentage=max_savings_pct,
            cherry_pick_total=cherry_pick_total,
            cherry_pick_savings=cherry_pick_savings,
            cherry_pick_savings_percentage=cherry_pick_savings_pct,
            items_matrix=items_matrix,
            quotations=quotations_results,
            warnings=self.warnings,
        )

    def _compare_single_rfq_item(
        self,
        rfq_item,
        normalized_quotes_map: Dict[str, Optional[NormalizedQuotation]],
        quote_currency_errors: Dict[str, str],
    ) -> LineItemComparisonResult:
        """
        Compares all supplier bids for a single RFQ item.
        Computes lowest comparable unit price, extended prices, spreads, and item rankings.
        """
        rfq_item_id = str(rfq_item.id)
        target_qty = to_decimal(getattr(rfq_item, 'quantity', '1.00'))
        target_unit = (getattr(rfq_item, 'unit', 'EA') or 'EA').strip()
        target_price = to_decimal(getattr(rfq_item, 'target_unit_price', None)) if getattr(rfq_item, 'target_unit_price', None) is not None else None

        bids: Dict[str, SupplierItemBid] = {}

        for quote in self.raw_quotations:
            quote_id = str(quote.id)
            supplier = getattr(quote, 'supplier', None)
            supplier_id = str(supplier.id) if supplier else f"sup_{quote_id[:8]}"
            supplier_name = getattr(supplier, 'company_name', getattr(quote, 'supplier_name', 'Unknown Supplier'))
            quote_number = getattr(quote, 'quotation_number', '')

            # Currency conversion block
            if quote_id in quote_currency_errors:
                # Missing rate: cannot calculate comparable bid
                continue

            norm = normalized_quotes_map.get(quote_id)
            if norm and norm.financials.normalized_currency != self.comparison_currency:
                # Quotation currency could not be converted to comparison currency
                continue

            # Find matching item in quotation items
            matching_raw_item = None
            matching_norm_item = None

            # First match by rfq_item foreign key
            if hasattr(quote, 'items'):
                for q_it in quote.items.all():
                    if q_it.rfq_item_id and str(q_it.rfq_item_id) == rfq_item_id:
                        matching_raw_item = q_it
                        break
                    # Fallback match by position or name
                    elif q_it.position == getattr(rfq_item, 'position', -1):
                        matching_raw_item = q_it
                        break

            # Match in normalized items
            if norm:
                for n_it in norm.items:
                    if n_it.rfq_item_id and str(n_it.rfq_item_id) == rfq_item_id:
                        matching_norm_item = n_it
                        break
                    elif n_it.line_number == getattr(rfq_item, 'position', -1):
                        matching_norm_item = n_it
                        break

            if not matching_raw_item and not matching_norm_item:
                # Supplier did not quote this item
                continue

            # Extract quoted and normalized figures
            quoted_qty = to_decimal(getattr(matching_raw_item, 'quantity', getattr(matching_norm_item, 'native_quantity', target_qty)))
            quoted_unit = getattr(matching_raw_item, 'unit', getattr(matching_norm_item, 'native_unit', target_unit))
            quoted_unit_price = to_decimal(getattr(matching_raw_item, 'unit_price', getattr(matching_norm_item, 'native_unit_price', '0.00')))
            quoted_disc = to_decimal(getattr(matching_raw_item, 'discount', getattr(matching_norm_item, 'native_discount', '0.00')))
            quoted_tax = to_decimal(getattr(matching_raw_item, 'tax', getattr(matching_norm_item, 'native_tax', '0.00')))
            stated_line_total = to_decimal(getattr(matching_raw_item, 'line_total', getattr(matching_norm_item, 'native_total', '0.00')))

            # Check raw math inconsistency
            _, raw_math_inc = ComparisonValidator.check_line_item_math(
                quantity=quoted_qty,
                unit_price=quoted_unit_price,
                stated_line_total=stated_line_total,
                discount=quoted_disc,
                tax=quoted_tax,
                line_identifier=f"Quotation {quote_number} Line {getattr(rfq_item, 'position', 1)}",
            )
            item_inconsistencies = [raw_math_inc] if raw_math_inc else []

            # Normalized figures in comparison currency & RFQ UOM
            if matching_norm_item:
                norm_qty = to_decimal(matching_norm_item.normalized_quantity)
                norm_unit = matching_norm_item.normalized_unit
                norm_unit_price = to_decimal(matching_norm_item.normalized_unit_price)
                norm_disc = to_decimal(matching_norm_item.native_discount)
                norm_tax = to_decimal(matching_norm_item.native_tax)
            else:
                norm_qty = quoted_qty
                norm_unit = quoted_unit
                norm_unit_price = quoted_unit_price
                norm_disc = quoted_disc
                norm_tax = quoted_tax

            # Extended prices
            # 1. Extended price for quoted quantity: Qty * UnitPrice - Disc + Tax
            ext_price_quoted = calculate_extended_price(quoted_qty, norm_unit_price, norm_disc, norm_tax)
            # 2. Re-scaled extended price for target RFQ quantity: TargetQty * NormalizedUnitPrice
            ext_price_target = calculate_scaled_target_price(target_qty, norm_unit_price)

            # Determine compatibility
            compat_status, compat_reason = ComparisonValidator.determine_item_compatibility(
                rfq_item=rfq_item,
                quote_item=matching_raw_item,
                normalized_quote_item=matching_norm_item,
            )

            material_spec = getattr(matching_raw_item, 'specifications', '') or ''
            has_spec_variance = compat_status == ItemCompatibilityStatus.SPEC_VARIANCE

            # Detailed Specification Matching if specifications exist on both RFQ and Quote
            spec_summary_dict = None
            rfq_has_specs = bool(
                getattr(rfq_item, 'custom_specifications', None)
                or (hasattr(rfq_item, 'specifications') and hasattr(rfq_item.specifications, 'exists') and rfq_item.specifications.exists())
            )
            quote_has_specs = bool(getattr(matching_raw_item, 'specifications', None))

            if rfq_has_specs and quote_has_specs:
                try:
                    from comparisons.specs import SpecificationMatchingEngine, SpecVerdict, SpecMatchStatus
                    spec_engine = SpecificationMatchingEngine()
                    item_spec_summary = spec_engine.compare_item_specifications(
                        rfq_item_or_specs=rfq_item,
                        supplier_item_or_specs=matching_raw_item,
                        item_name=getattr(rfq_item, 'item_name', 'Line Item'),
                        use_ai=False,
                    )
                    spec_summary_dict = item_spec_summary.to_dict()

                    if item_spec_summary.has_critical_mismatches or item_spec_summary.verdict == SpecVerdict.NON_COMPLIANT:
                        compat_status = ItemCompatibilityStatus.INCOMPATIBLE
                        mismatch_reasons = [m.explanation for m in item_spec_summary.matches if m.status == SpecMatchStatus.MISMATCH]
                        compat_reason = f"Technical specification conflict: {'; '.join(mismatch_reasons)}"
                        has_spec_variance = True
                    elif item_spec_summary.verdict in (SpecVerdict.SPEC_VARIANCE, SpecVerdict.INCOMPLETE) or item_spec_summary.spec_match_score < 100.0:
                        if compat_status != ItemCompatibilityStatus.INCOMPATIBLE:
                            compat_status = ItemCompatibilityStatus.SPEC_VARIANCE
                        variance_notes = [m.explanation for m in item_spec_summary.matches if m.status in (SpecMatchStatus.MISMATCH, SpecMatchStatus.UNCLEAR, SpecMatchStatus.MISSING)]
                        compat_reason = f"Specification variance ({item_spec_summary.spec_match_score:.1f}%): {'; '.join(variance_notes)}"
                        has_spec_variance = True
                except Exception as spec_exc:
                    logger.warning("Could not execute specification matching during price comparison: %s", spec_exc)

            bid = SupplierItemBid(
                quotation_id=quote_id,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                quote_number=quote_number,
                quoted_quantity=quoted_qty,
                quoted_unit=quoted_unit,
                quoted_unit_price=quoted_unit_price,
                quoted_line_total=stated_line_total,
                normalized_quantity=norm_qty,
                normalized_unit=norm_unit,
                normalized_unit_price=quantize_unit_price(norm_unit_price),
                normalized_line_discount=norm_disc,
                normalized_line_tax=norm_tax,
                extended_price_quoted_qty=ext_price_quoted,
                extended_price_target_qty=ext_price_target,
                compatibility_status=compat_status,
                incompatibility_reason=compat_reason,
                material_spec_quoted=material_spec if isinstance(material_spec, str) else str(material_spec),
                has_spec_variance=has_spec_variance,
                spec_variance_notes=compat_reason if has_spec_variance else '',
                has_calculation_inconsistency=bool(item_inconsistencies),
                inconsistencies=item_inconsistencies,
                spec_summary=spec_summary_dict,
            )
            bids[supplier_id] = bid

        # 4. Filter comparable bids for lowest price identification
        eligible_bids = [
            bid for bid in bids.values()
            if bid.compatibility_status in (ItemCompatibilityStatus.COMPATIBLE, ItemCompatibilityStatus.SPEC_VARIANCE)
            or self.include_incompatible_in_lowest
        ]

        lowest_unit_price = None
        lowest_ext_price = None
        lowest_bidder_id = None
        lowest_bidder_name = None
        highest_ext_price = None
        average_ext_price = None
        spread_amount = Decimal('0.00')
        spread_percentage = Decimal('0.00')

        if eligible_bids:
            lowest_unit_price = min((bid.normalized_unit_price for bid in eligible_bids))
            lowest_ext_price = min((bid.extended_price_target_qty for bid in eligible_bids))
            highest_ext_price = max((bid.extended_price_target_qty for bid in eligible_bids))

            total_ext = sum((bid.extended_price_target_qty for bid in eligible_bids), Decimal('0.00'))
            average_ext_price = quantize_currency(total_ext / Decimal(len(eligible_bids)))

            spread_amount = quantize_currency(highest_ext_price - lowest_ext_price)
            spread_percentage = calculate_percentage_difference(highest_ext_price, lowest_ext_price)

            # Assign ranks and variances for all bids
            ranked_bids = assign_ranks(eligible_bids, key_func=lambda b: b.extended_price_target_qty)

            for rank, bid in ranked_bids:
                bid.item_rank = rank
                bid.price_difference = calculate_price_difference(bid.extended_price_target_qty, lowest_ext_price)
                bid.percentage_difference = calculate_percentage_difference(bid.extended_price_target_qty, lowest_ext_price)
                bid.is_lowest_unit_price = (bid.normalized_unit_price == lowest_unit_price)
                bid.is_lowest_extended_price = (bid.extended_price_target_qty == lowest_ext_price)

                if bid.is_lowest_extended_price and not lowest_bidder_id:
                    lowest_bidder_id = bid.supplier_id
                    lowest_bidder_name = bid.supplier_name

            # Also rank any non-eligible/incompatible bids with default rank
            for bid in bids.values():
                if bid not in eligible_bids:
                    bid.item_rank = len(eligible_bids) + 1
                    if lowest_ext_price:
                        bid.price_difference = calculate_price_difference(bid.extended_price_target_qty, lowest_ext_price)
                        bid.percentage_difference = calculate_percentage_difference(bid.extended_price_target_qty, lowest_ext_price)

        return LineItemComparisonResult(
            rfq_item_id=rfq_item_id,
            position=getattr(rfq_item, 'position', 1),
            item_name=getattr(rfq_item, 'item_name', '') or getattr(rfq_item, 'description', f'Item {rfq_item_id[:6]}'),
            description=getattr(rfq_item, 'description', ''),
            target_quantity=target_qty,
            target_unit=target_unit,
            target_unit_price=target_price,
            bids=bids,
            lowest_unit_price=lowest_unit_price,
            lowest_extended_price=lowest_ext_price,
            lowest_bidder_id=lowest_bidder_id,
            lowest_bidder_name=lowest_bidder_name,
            highest_extended_price=highest_ext_price,
            average_extended_price=average_ext_price,
            spread_amount=spread_amount,
            spread_percentage=spread_percentage,
        )

    def _reconcile_quotation_comparison(
        self,
        quote,
        norm: Optional[NormalizedQuotation],
        items_matrix: List[LineItemComparisonResult],
        total_rfq_items_count: int,
        currency_error: Optional[str] = None,
    ) -> QuotationComparisonResult:
        """
        Reconciles financial totals and commercial terms for a single quotation.
        Audits subtotal and grand total math against document stated figures.
        """
        quote_id = str(quote.id)
        supplier = getattr(quote, 'supplier', None)
        supplier_id = str(supplier.id) if supplier else f"sup_{quote_id[:8]}"
        supplier_name = getattr(supplier, 'company_name', getattr(quote, 'supplier_name', 'Unknown Supplier'))
        quote_number = getattr(quote, 'quotation_number', '')

        native_curr = getattr(quote, 'currency', self.comparison_currency)
        rate_applied = None
        rate_source = ''
        rate_date = None

        if norm and norm.financials.currency_conversion and not norm.financials.currency_conversion.is_identity:
            conv = norm.financials.currency_conversion
            rate_applied = conv.exchange_rate
            rate_source = conv.rate_source
            rate_date = conv.rate_date

        # Check covered items in RFQ
        covered_count = 0
        unquoted_item_ids = []
        target_scaled_subtotal = Decimal('0.00')

        for item_res in items_matrix:
            if supplier_id in item_res.bids:
                covered_count += 1
                target_scaled_subtotal += item_res.bids[supplier_id].extended_price_target_qty
            else:
                unquoted_item_ids.append(item_res.rfq_item_id)

        is_full_coverage = (covered_count == total_rfq_items_count)
        coverage_pct = (
            quantize_percentage((Decimal(covered_count) / Decimal(total_rfq_items_count)) * Decimal('100.0'))
            if total_rfq_items_count > 0
            else Decimal('100.00')
        )

        # Financial totals
        if norm:
            subtotal = norm.financials.normalized_subtotal
            discounts = norm.financials.normalized_discount
            taxes = norm.financials.normalized_tax
            shipping = norm.financials.normalized_shipping
            grand_total = norm.financials.normalized_grand_total

            stated_subtotal = norm.financials.native_subtotal
            stated_grand_total = norm.financials.native_grand_total
        else:
            subtotal = to_decimal(getattr(quote, 'subtotal', '0.00'))
            discounts = Decimal('0.00')
            taxes = to_decimal(getattr(quote, 'tax_amount', '0.00'))
            shipping = Decimal('0.00')
            grand_total = to_decimal(getattr(quote, 'total_amount', '0.00'))
            stated_subtotal = subtotal
            stated_grand_total = grand_total

        # Target Scaled Grand Total: scale subtotal + taxes + shipping - discount
        target_scaled_grand_total = calculate_grand_total(target_scaled_subtotal, discounts, taxes, shipping)

        # Check subtotal & grand total math inconsistency
        reconciled_gt, total_inconsistencies = ComparisonValidator.check_quotation_totals_math(
            calculated_subtotal=subtotal,
            stated_subtotal=stated_subtotal if native_curr == self.comparison_currency else None,
            order_discount=discounts,
            order_tax=taxes,
            shipping=shipping,
            stated_grand_total=stated_grand_total if native_curr == self.comparison_currency else None,
        )

        # Comparability determination
        is_comparable = True
        incomparability_reasons: List[str] = []

        if currency_error:
            is_comparable = False
            incomparability_reasons.append(f"Currency conversion failed: {currency_error}")

        if norm and norm.financials.normalized_currency != self.comparison_currency:
            is_comparable = False
            incomparability_reasons.append(
                f"Quotation currency ({norm.financials.normalized_currency}) differs from comparison currency "
                f"({self.comparison_currency}) and no exchange rate was found in corporate exchange rates."
            )

        if not is_full_coverage:
            incomparability_reasons.append(
                f"Partial coverage: Quoted {covered_count} of {total_rfq_items_count} required items."
            )

        # Commercial terms extraction
        comm = getattr(quote, 'commercial_terms', None) or {}
        lead_weeks = int(getattr(quote, 'lead_time_weeks', 0) or 0)
        pay_terms = getattr(quote, 'payment_terms', '') or ''
        warranty_str = getattr(quote, 'warranty_information', '') or ''
        incoterms = getattr(quote, 'delivery_terms', '') or ''

        if norm:
            lead_weeks = int(norm.commercial_terms.lead_time.lead_time_weeks) or lead_weeks
            lead_days = norm.commercial_terms.lead_time.representative_days or (lead_weeks * 7)
            pay_terms = norm.commercial_terms.payment_terms.summary or pay_terms
            warranty_months = norm.commercial_terms.warranty.duration_months or 0
            warranty_str = norm.commercial_terms.warranty.raw_text or warranty_str
            incoterms = norm.commercial_terms.delivery_terms or incoterms
        else:
            lead_days = lead_weeks * 7
            warranty_months = 0

        return QuotationComparisonResult(
            quotation_id=quote_id,
            quotation_number=quote_number,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            quote_date=getattr(quote, 'quotation_date', None),
            valid_until=getattr(quote, 'validity_date', None),
            native_currency=native_curr,
            comparison_currency=self.comparison_currency,
            exchange_rate_applied=rate_applied,
            rate_source=rate_source,
            rate_date=rate_date,
            total_rfq_items=total_rfq_items_count,
            covered_items_count=covered_count,
            coverage_percentage=coverage_pct,
            is_full_coverage=is_full_coverage,
            unquoted_item_ids=unquoted_item_ids,
            subtotal=subtotal,
            discounts=discounts,
            taxes=taxes,
            shipping=shipping,
            grand_total=grand_total,
            target_scaled_grand_total=target_scaled_grand_total,
            stated_subtotal=stated_subtotal,
            stated_grand_total=stated_grand_total,
            has_calculation_inconsistencies=bool(total_inconsistencies),
            inconsistencies=total_inconsistencies,
            is_comparable=is_comparable,
            incomparability_reasons=incomparability_reasons,
            delivery_lead_weeks=lead_weeks,
            delivery_lead_days=lead_days,
            payment_terms=pay_terms,
            warranty_months=warranty_months,
            warranty_terms=warranty_str,
            incoterms=incoterms,
            notes=getattr(quote, 'notes', '') or '',
        )

    def _rank_and_benchmark_quotations(
        self,
        quotations_results: List[QuotationComparisonResult],
    ) -> None:
        """
        Ranks quotations by grand total (lowest cost = Rank 1).
        Computes price differences, percentage variances, and potential savings.
        """
        # We rank comparable full-coverage quotations first
        comparable_quotes = [q for q in quotations_results if q.is_comparable and q.is_full_coverage]

        # If no full coverage quote exists, fallback to any comparable quote
        if not comparable_quotes:
            comparable_quotes = [q for q in quotations_results if q.is_comparable]

        if not comparable_quotes:
            # None are comparable (e.g. all missing exchange rates)
            for q in quotations_results:
                q.rank = 1
            return

        lowest_grand_total = min((q.grand_total for q in comparable_quotes))

        ranked_quotes = assign_ranks(comparable_quotes, key_func=lambda q: q.grand_total)

        for rank, quote_res in ranked_quotes:
            quote_res.rank = rank
            quote_res.is_lowest_grand_total = (quote_res.grand_total == lowest_grand_total)
            quote_res.price_difference_vs_lowest = calculate_price_difference(quote_res.grand_total, lowest_grand_total)
            quote_res.percentage_difference_vs_lowest = calculate_percentage_difference(quote_res.grand_total, lowest_grand_total)
            quote_res.potential_savings_vs_this_quote = calculate_savings_amount(quote_res.grand_total, lowest_grand_total)

        # Non-comparable quotes get placed after all comparable ones
        next_rank = len(comparable_quotes) + 1
        for q in quotations_results:
            if q not in comparable_quotes:
                q.rank = next_rank
                q.price_difference_vs_lowest = calculate_price_difference(q.grand_total, lowest_grand_total)
                q.percentage_difference_vs_lowest = calculate_percentage_difference(q.grand_total, lowest_grand_total)

    @staticmethod
    def _calculate_median(values: List[Decimal]) -> Decimal:
        """Calculates deterministic median for a list of Decimals."""
        if not values:
            return Decimal('0.00')
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 1:
            return quantize_currency(sorted_vals[mid])
        return quantize_currency((sorted_vals[mid - 1] + sorted_vals[mid]) / Decimal('2.0'))
