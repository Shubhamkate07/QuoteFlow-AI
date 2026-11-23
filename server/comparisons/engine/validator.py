"""
Deterministic Validation and Inconsistency Detection Engine for Quotation Price Comparison.
Verifies data integrity, cross-tenant isolation, line item compatibility,
and detects mathematical discrepancies between vendor documents and verified arithmetic.
"""
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .formulas import (
    CENT_PRECISION,
    calculate_extended_price,
    calculate_grand_total,
    calculate_subtotal,
    quantize_currency,
    to_decimal,
)
from .schemas import (
    CalculationInconsistency,
    InconsistencySeverity,
    ItemCompatibilityStatus,
)

logger = logging.getLogger('quoteflow.comparisons.validator')

# Tolerance in currency units before flagging an inconsistency as an ERROR
ROUNDING_TOLERANCE = Decimal('0.05')
SUBSTANTIAL_VARIANCE_THRESHOLD = Decimal('2.00')


class ComparisonValidationError(Exception):
    """Raised when deterministic validation encounters an unrecoverable comparison error."""
    pass


class ComparisonValidator:
    """
    Validates RFQs, Quotations, and Line Items for multi-vendor price comparison.
    Identifies document math discrepancies without altering original records.
    """

    @classmethod
    def validate_rfq_for_comparison(cls, rfq) -> List[str]:
        """
        Validates that the RFQ is eligible for comparison.
        Returns a list of non-fatal warnings (if any).
        """
        if not rfq:
            raise ComparisonValidationError("RFQ instance is required for quotation comparison.")

        items_count = rfq.items.count() if hasattr(rfq, 'items') else len(getattr(rfq, 'rfq_items', []))
        if items_count == 0:
            raise ComparisonValidationError(
                f"RFQ #{getattr(rfq, 'rfq_number', rfq.id)} has no defined line items to compare against."
            )

        warnings: List[str] = []
        if not getattr(rfq, 'currency', None):
            warnings.append("RFQ has no designated default currency; falling back to USD.")

        return warnings

    @classmethod
    def validate_tenant_isolation(cls, rfq, quotations: List[Any]) -> None:
        """
        Guarantees that all quotations belong to the exact same organization as the RFQ.
        Strict multi-tenant security boundary.
        """
        rfq_org_id = getattr(rfq, 'organization_id', None) or getattr(rfq, 'organization', None)
        for quote in quotations:
            quote_org_id = getattr(quote, 'organization_id', None) or getattr(quote, 'organization', None)
            if rfq_org_id and quote_org_id and str(rfq_org_id) != str(quote_org_id):
                raise ComparisonValidationError(
                    f"Security violation: Quotation {quote.id} does not belong to the RFQ's organization."
                )

    @classmethod
    def check_line_item_math(
        cls,
        quantity: Any,
        unit_price: Any,
        stated_line_total: Any,
        discount: Any = '0.00',
        tax: Any = '0.00',
        line_identifier: str = 'item',
    ) -> Tuple[Decimal, Optional[CalculationInconsistency]]:
        """
        Validates line item arithmetic:
            Calculated = (Quantity * Unit Price) - Discount + Tax
        Returns (reconciled_line_total, optional_inconsistency).
        """
        qty = to_decimal(quantity)
        price = to_decimal(unit_price)
        disc = to_decimal(discount)
        tx = to_decimal(tax)
        stated = to_decimal(stated_line_total)

        calculated = calculate_extended_price(qty, price, disc, tx)
        variance = quantize_currency(stated - calculated)

        inconsistency = None
        if abs(variance) > ROUNDING_TOLERANCE:
            severity = (
                InconsistencySeverity.ERROR
                if abs(variance) > SUBSTANTIAL_VARIANCE_THRESHOLD
                else InconsistencySeverity.WARNING
            )
            inconsistency = CalculationInconsistency(
                scope='line_item',
                field_name=f"{line_identifier}.line_total",
                stated_value=stated,
                calculated_value=calculated,
                variance=variance,
                severity=severity,
                explanation=(
                    f"Stated line total ({stated}) differs from verified price "
                    f"({qty} * {price} - {disc} + {tx} = {calculated}) by {variance}."
                ),
            )

        return calculated, inconsistency

    @classmethod
    def check_quotation_totals_math(
        cls,
        calculated_subtotal: Decimal,
        stated_subtotal: Optional[Decimal],
        order_discount: Any,
        order_tax: Any,
        shipping: Any,
        stated_grand_total: Optional[Decimal],
    ) -> Tuple[Decimal, List[CalculationInconsistency]]:
        """
        Validates subtotal and grand total arithmetic across the entire quotation.
        Returns (reconciled_grand_total, list_of_inconsistencies).
        """
        inconsistencies: List[CalculationInconsistency] = []
        disc = to_decimal(order_discount)
        tx = to_decimal(order_tax)
        ship = to_decimal(shipping)

        # 1. Subtotal verification
        if stated_subtotal is not None:
            stated_sub = to_decimal(stated_subtotal)
            sub_variance = quantize_currency(stated_sub - calculated_subtotal)
            if abs(sub_variance) > ROUNDING_TOLERANCE:
                severity = (
                    InconsistencySeverity.ERROR
                    if abs(sub_variance) > SUBSTANTIAL_VARIANCE_THRESHOLD
                    else InconsistencySeverity.WARNING
                )
                inconsistencies.append(
                    CalculationInconsistency(
                        scope='subtotal',
                        field_name='subtotal',
                        stated_value=stated_sub,
                        calculated_value=calculated_subtotal,
                        variance=sub_variance,
                        severity=severity,
                        explanation=(
                            f"Stated subtotal ({stated_sub}) differs from the sum of line items "
                            f"({calculated_subtotal}) by {sub_variance}."
                        ),
                    )
                )

        # 2. Grand total verification
        reconciled_grand_total = calculate_grand_total(calculated_subtotal, disc, tx, ship)

        if stated_grand_total is not None:
            stated_gt = to_decimal(stated_grand_total)
            gt_variance = quantize_currency(stated_gt - reconciled_grand_total)
            if abs(gt_variance) > ROUNDING_TOLERANCE:
                severity = (
                    InconsistencySeverity.ERROR
                    if abs(gt_variance) > SUBSTANTIAL_VARIANCE_THRESHOLD
                    else InconsistencySeverity.WARNING
                )
                inconsistencies.append(
                    CalculationInconsistency(
                        scope='grand_total',
                        field_name='grand_total',
                        stated_value=stated_gt,
                        calculated_value=reconciled_grand_total,
                        variance=gt_variance,
                        severity=severity,
                        explanation=(
                            f"Stated grand total ({stated_gt}) differs from calculated total "
                            f"({calculated_subtotal} - {disc} + {tx} + {ship} = {reconciled_grand_total}) "
                            f"by {gt_variance}."
                        ),
                    )
                )

        return reconciled_grand_total, inconsistencies

    @classmethod
    def determine_item_compatibility(
        cls,
        rfq_item,
        quote_item,
        normalized_quote_item=None,
    ) -> Tuple[ItemCompatibilityStatus, str]:
        """
        Determines whether a quoted item can be fairly compared against the RFQ item.
        Checks UoM compatibility and specification variance.
        """
        # 1. Unit of Measure Category Check
        rfq_unit = (getattr(rfq_item, 'unit', '') or '').strip().lower()
        quote_unit = (getattr(quote_item, 'unit', '') or '').strip().lower()

        if normalized_quote_item:
            category = getattr(normalized_quote_item, 'uom_category', '')
            if category == 'incompatible':
                return (
                    ItemCompatibilityStatus.INCOMPATIBLE,
                    f"Unit of measure '{quote_unit}' cannot be converted to RFQ unit '{rfq_unit}'.",
                )

        # 2. Explicit match_type flag
        match_type = getattr(quote_item, 'match_type', 'exact') or 'exact'
        if match_type in ('variance', 'partial'):
            notes = getattr(quote_item, 'specifications', '') or getattr(quote_item, 'notes', '') or 'Specification variance noted'
            return (
                ItemCompatibilityStatus.SPEC_VARIANCE,
                f"Quoted item has specification variance: {notes}",
            )
        elif match_type == 'incompatible':
            return (
                ItemCompatibilityStatus.INCOMPATIBLE,
                "Item explicitly flagged as incompatible with RFQ specifications.",
            )

        # 3. Model/Manufacturer Preference Deviation Check
        mfr_pref = getattr(rfq_item, 'manufacturer_preference', '') or ''
        model_pref = getattr(rfq_item, 'model_preference', '') or ''
        quoted_mfr = getattr(quote_item, 'manufacturer', '') or ''
        quoted_model = getattr(quote_item, 'model', '') or ''

        if mfr_pref and quoted_mfr and mfr_pref.strip().lower() != quoted_mfr.strip().lower():
            return (
                ItemCompatibilityStatus.SPEC_VARIANCE,
                f"Quoted manufacturer '{quoted_mfr}' differs from RFQ preference '{mfr_pref}'.",
            )

        if model_pref and quoted_model and model_pref.strip().lower() != quoted_model.strip().lower():
            return (
                ItemCompatibilityStatus.SPEC_VARIANCE,
                f"Quoted model '{quoted_model}' differs from RFQ preference '{model_pref}'.",
            )

        return (ItemCompatibilityStatus.COMPATIBLE, '')
