"""
Deterministic Risk Evaluators for Quotation Risk Flag Engine.
Pure Python implementations of commercial, technical, and mathematical validation rules.
AI is NEVER used to generate these underlying flags.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from comparisons.risk.config import RiskEngineConfig
from comparisons.risk.schemas import RiskFlag, RiskFlagType, RiskSeverity


def _to_decimal(val: Any, default: str = '0.00') -> Decimal:
    """Safe decimal converter for robust arithmetic."""
    if val is None or val == '':
        return Decimal(default)
    try:
        return Decimal(str(val).strip())
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _to_date(val: Any) -> Optional[date]:
    """Safe date parser from date, datetime, or ISO string."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                continue
    return None


def extract_advance_payment_percentage(payment_terms: str) -> Optional[float]:
    """
    Deterministically extracts advance payment percentage from commercial payment terms.
    Examples:
        - "100% advance" -> 100.0
        - "50% advance, 50% on dispatch" -> 50.0
        - "30% down payment, balance net 30" -> 30.0
        - "Payment in advance" -> 100.0
        - "Full advance payment required" -> 100.0
        - "Cash in advance" -> 100.0
        - "Net 30" -> None
    """
    if not payment_terms or not payment_terms.strip():
        return None

    clean = payment_terms.lower().strip()

    # Explicit 100% advance phrases
    if any(phrase in clean for phrase in [
        'full advance', '100% advance', '100 % advance', 'payment in advance',
        'cash in advance', '100% upfront', 'prepayment in full', 'cia'
    ]):
        return 100.0

    # Numeric percentage patterns: e.g. "50% advance", "30 % down payment", "20% upfront"
    pattern = r'(\d+(?:\.\d+)?)\s*%\s*(?:advance|down\s*payment|upfront|prepayment|deposit|before\s*(?:shipment|dispatch|delivery))'
    match = re.search(pattern, clean)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    # Inverted pattern: e.g. "advance 50%", "down payment of 30%"
    inv_pattern = r'(?:advance|down\s*payment|deposit)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%'
    inv_match = re.search(inv_pattern, clean)
    if inv_match:
        try:
            return float(inv_match.group(1))
        except ValueError:
            pass

    return None


def check_payment_risk_terms(payment_terms: str) -> Optional[str]:
    """
    Identifies high-risk commercial payment terms that deviate from standard procurement credit.
    """
    if not payment_terms or not payment_terms.strip():
        return None

    clean = payment_terms.lower().strip()
    risky_patterns = [
        ('cash on delivery', 'Cash on Delivery (COD) requires immediate liquid funds and lacks inspection safeguards.'),
        ('cod', 'COD terms require payment before quality inspection or testing.'),
        ('wire transfer prior to dispatch', 'Full wire transfer prior to dispatch without security shifts 100% performance risk to buyer.'),
        ('wire transfer before shipment', 'Payment required before shipment shifts complete transit and performance risk to buyer.'),
        ('immediate payment', 'Immediate payment requirement allows zero commercial credit or invoice reconciliation window.'),
        ('letter of credit at buyer expense', 'LC at buyer expense adds substantial financial overhead and bank fees.'),
    ]

    for term, reason in risky_patterns:
        if term in clean:
            return reason

    return None


def check_warranty_disclaimer(warranty_text: str) -> bool:
    """
    Checks if a quotation explicitly disclaims or waives warranty coverage.
    """
    if not warranty_text or not warranty_text.strip():
        return False

    clean = warranty_text.lower().strip()
    disclaimer_phrases = [
        'no warranty', 'as-is', 'as is', 'without warranty', 'sold as seen',
        'no guarantee', 'without guarantee', '0 month', '0 days', '0 year',
        'warranty waived', 'warranty disclaimer', 'not covered by warranty',
    ]
    return any(phrase in clean for phrase in disclaimer_phrases)


# =========================================================================
# DOMAIN EVALUATORS
# =========================================================================

def evaluate_validity_risks(
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
    evaluation_date: Optional[date] = None,
) -> List[RiskFlag]:
    """Evaluates quotation validity date for expiry or missing commitment."""
    flags: List[RiskFlag] = []
    eval_dt = evaluation_date or date.today()
    val_dt = _to_date(quotation_data.get('validity_date'))

    if not val_dt:
        if config.is_rule_enabled(RiskFlagType.MISSING_QUOTATION_VALIDITY):
            flags.append(
                RiskFlag(
                    type=RiskFlagType.MISSING_QUOTATION_VALIDITY,
                    severity=RiskSeverity.WARNING,
                    title="Missing Quotation Validity Period",
                    description="The quotation does not state an expiration or validity date for the quoted pricing and terms.",
                    affected_field_or_item="validity_date",
                    evidence="Validity date field is empty or unstated.",
                    recommended_action="Request supplier to confirm in writing how long quoted pricing and delivery terms remain valid.",
                )
            )
    else:
        if val_dt < eval_dt and config.is_rule_enabled(RiskFlagType.EXPIRED_QUOTATION):
            days_expired = (eval_dt - val_dt).days
            flags.append(
                RiskFlag(
                    type=RiskFlagType.EXPIRED_QUOTATION,
                    severity=RiskSeverity.CRITICAL,
                    title=f"Quotation Expired on {val_dt.isoformat()}",
                    description=(
                        f"The quotation validity period expired on {val_dt.isoformat()} ({days_expired} days ago). "
                        "The supplier is legally no longer bound to honor quoted pricing or delivery schedules."
                    ),
                    affected_field_or_item="validity_date",
                    evidence=f"Validity date: {val_dt.isoformat()}, Current evaluation date: {eval_dt.isoformat()}",
                    recommended_action="Request a formal quotation extension or updated quote before issuing a purchase order.",
                    metadata={'days_expired': days_expired, 'validity_date': val_dt.isoformat()},
                )
            )

    return flags


def evaluate_payment_risks(
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Evaluates commercial payment terms for advance payment exposure and payment risks."""
    flags: List[RiskFlag] = []
    payment_terms = str(quotation_data.get('payment_terms', '') or '').strip()

    if not payment_terms:
        return flags

    # 1. Advance Payment Percentage Check
    advance_pct = extract_advance_payment_percentage(payment_terms)
    if advance_pct is not None and config.is_rule_enabled(RiskFlagType.HIGH_ADVANCE_PAYMENT):
        if advance_pct >= config.advance_payment_critical_threshold_pct:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.HIGH_ADVANCE_PAYMENT,
                    severity=RiskSeverity.CRITICAL,
                    title=f"High Advance Payment Demanded ({advance_pct:.0f}%)",
                    description=(
                        f"Supplier requires an advance payment of {advance_pct:.0f}%, which meets or exceeds the critical "
                        f"threshold of {config.advance_payment_critical_threshold_pct:.0f}%. "
                        "This exposes the buyer to significant cash flow and supplier non-performance risk."
                    ),
                    affected_field_or_item="payment_terms",
                    evidence=f"Quoted payment terms: '{payment_terms}' (extracted {advance_pct:.0f}% advance).",
                    recommended_action="Negotiate staged milestone payments tied to quality inspection, or require an Advance Payment Guarantee (APG).",
                    metadata={'advance_percentage': advance_pct},
                )
            )
        elif advance_pct >= config.advance_payment_warning_threshold_pct:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.HIGH_ADVANCE_PAYMENT,
                    severity=RiskSeverity.WARNING,
                    title=f"Moderate Advance Payment Required ({advance_pct:.0f}%)",
                    description=(
                        f"Supplier requires an advance payment of {advance_pct:.0f}%, exceeding the warning "
                        f"threshold of {config.advance_payment_warning_threshold_pct:.0f}%."
                    ),
                    affected_field_or_item="payment_terms",
                    evidence=f"Quoted payment terms: '{payment_terms}' (extracted {advance_pct:.0f}% advance).",
                    recommended_action="Attempt to negotiate lower down payment or balance payment on delivery (e.g. Net 30).",
                    metadata={'advance_percentage': advance_pct},
                )
            )

    # 2. General Commercial Payment Risk
    if config.is_rule_enabled(RiskFlagType.PAYMENT_RISK):
        risk_reason = check_payment_risk_terms(payment_terms)
        if risk_reason:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.PAYMENT_RISK,
                    severity=RiskSeverity.WARNING,
                    title="Unfavorable Commercial Payment Terms",
                    description=risk_reason,
                    affected_field_or_item="payment_terms",
                    evidence=f"Quoted payment terms: '{payment_terms}'.",
                    recommended_action="Request standard corporate credit terms (e.g. Net 30 or Net 60 from invoice date).",
                )
            )

    return flags


def evaluate_warranty_risks(
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Evaluates warranty coverage for explicit disclaimers or missing warranty."""
    flags: List[RiskFlag] = []
    warranty_info = str(quotation_data.get('warranty_information', '') or '').strip()

    if not warranty_info:
        if config.is_rule_enabled(RiskFlagType.MISSING_WARRANTY):
            flags.append(
                RiskFlag(
                    type=RiskFlagType.MISSING_WARRANTY,
                    severity=RiskSeverity.WARNING,
                    title="Unspecified Warranty Coverage",
                    description="The quotation does not state any warranty duration, coverage limits, or replacement policies.",
                    affected_field_or_item="warranty_information",
                    evidence="Warranty information field is empty.",
                    recommended_action=f"Require supplier to provide standard written warranty (minimum {config.min_acceptable_warranty_months} months).",
                )
            )
    else:
        if check_warranty_disclaimer(warranty_info) and config.is_rule_enabled(RiskFlagType.NO_WARRANTY):
            flags.append(
                RiskFlag(
                    type=RiskFlagType.NO_WARRANTY,
                    severity=RiskSeverity.CRITICAL,
                    title="Explicit Disclaimer of Warranty",
                    description=(
                        "Supplier explicitly disclaims warranty coverage ('as-is' or zero warranty). "
                        "Any equipment failure or defects upon receipt will require out-of-pocket buyer expense."
                    ),
                    affected_field_or_item="warranty_information",
                    evidence=f"Stated warranty: '{warranty_info}'.",
                    recommended_action="Reject 'as-is' terms and negotiate a mandatory warranty period before contracting.",
                )
            )

    return flags


def evaluate_administrative_risks(
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Checks for missing critical administrative quotation details."""
    flags: List[RiskFlag] = []
    if not config.is_rule_enabled(RiskFlagType.MISSING_QUOTATION_INFORMATION):
        return flags

    # Quotation Number
    quote_num = str(quotation_data.get('quotation_number', '') or '').strip()
    if not quote_num:
        flags.append(
            RiskFlag(
                type=RiskFlagType.MISSING_QUOTATION_INFORMATION,
                severity=RiskSeverity.WARNING,
                title="Missing Quotation Reference Number",
                description="The quotation does not contain an official quotation, proposal, or reference number.",
                affected_field_or_item="quotation_number",
                evidence="Quotation number is missing or empty.",
                recommended_action="Request official numbered quotation document for audit and PO referencing.",
            )
        )

    # Quotation Date
    quote_dt = quotation_data.get('quotation_date')
    if not quote_dt:
        flags.append(
            RiskFlag(
                type=RiskFlagType.MISSING_QUOTATION_INFORMATION,
                severity=RiskSeverity.WARNING,
                title="Missing Quotation Issue Date",
                description="The quotation does not state the date it was issued by the supplier.",
                affected_field_or_item="quotation_date",
                evidence="Quotation date is missing or unparsed.",
                recommended_action="Confirm the official quote issue date with supplier.",
            )
        )

    # Supplier Identification
    supp = quotation_data.get('supplier_name') or quotation_data.get('supplier')
    if not supp:
        flags.append(
            RiskFlag(
                type=RiskFlagType.MISSING_QUOTATION_INFORMATION,
                severity=RiskSeverity.WARNING,
                title="Unidentified Supplier Entity",
                description="The supplier corporate entity name is missing from the quotation records.",
                affected_field_or_item="supplier",
                evidence="Supplier name is empty.",
                recommended_action="Ensure supplier is properly onboarded and mapped in the supplier registry.",
            )
        )

    return flags


def evaluate_currency_risks(
    rfq_data: Optional[Dict[str, Any]],
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Identifies currency mismatches between RFQ requirement and supplier quotation."""
    flags: List[RiskFlag] = []
    if not rfq_data or not config.is_rule_enabled(RiskFlagType.CURRENCY_MISMATCH):
        return flags

    rfq_curr = (rfq_data.get('currency', '') or '').strip().upper()
    quote_curr = (quotation_data.get('currency', '') or '').strip().upper()

    if rfq_curr and quote_curr and rfq_curr != quote_curr:
        flags.append(
            RiskFlag(
                type=RiskFlagType.CURRENCY_MISMATCH,
                severity=RiskSeverity.WARNING,
                title=f"Currency Mismatch ({quote_curr} vs RFQ {rfq_curr})",
                description=(
                    f"Quotation was submitted in {quote_curr}, differing from the RFQ target currency {rfq_curr}. "
                    "Procurement is exposed to foreign exchange (FX) volatility and bank conversion fees."
                ),
                affected_field_or_item="currency",
                evidence=f"Quotation Currency: '{quote_curr}', RFQ Currency: '{rfq_curr}'.",
                recommended_action=f"Lock in a documented corporate exchange rate or request quotation re-issued in {rfq_curr}.",
                metadata={'rfq_currency': rfq_curr, 'quotation_currency': quote_curr},
            )
        )

    return flags


def evaluate_delivery_risks(
    rfq_data: Optional[Dict[str, Any]],
    quotation_data: Dict[str, Any],
    config: RiskEngineConfig,
    evaluation_date: Optional[date] = None,
) -> List[RiskFlag]:
    """Evaluates delivery delay against the RFQ required delivery date."""
    flags: List[RiskFlag] = []
    if not rfq_data or not config.is_rule_enabled(RiskFlagType.DELIVERY_DELAY):
        return flags

    rfq_req_date = _to_date(rfq_data.get('required_delivery_date'))
    if not rfq_req_date:
        return flags

    # 1. Check explicit quoted delivery date
    quoted_delivery_date = _to_date(quotation_data.get('delivery_date'))

    # 2. If no explicit date, estimate from quotation date + lead time
    if not quoted_delivery_date:
        lead_time_weeks = quotation_data.get('lead_time_weeks')
        lead_time_days = quotation_data.get('lead_time_days')
        quote_dt = _to_date(quotation_data.get('quotation_date')) or evaluation_date or date.today()

        if lead_time_weeks is not None:
            days = int(float(lead_time_weeks) * 7)
            quoted_delivery_date = quote_dt + timedelta(days=days)
        elif lead_time_days is not None:
            quoted_delivery_date = quote_dt + timedelta(days=int(lead_time_days))

    if quoted_delivery_date:
        effective_deadline = rfq_req_date + timedelta(days=config.delivery_delay_grace_days)
        if quoted_delivery_date > effective_deadline:
            delay_days = (quoted_delivery_date - rfq_req_date).days
            severity = (
                RiskSeverity.CRITICAL
                if delay_days >= config.delivery_delay_critical_days
                else RiskSeverity.WARNING
            )
            flags.append(
                RiskFlag(
                    type=RiskFlagType.DELIVERY_DELAY,
                    severity=severity,
                    title=f"Quoted Delivery Schedule Delay ({delay_days} days late)",
                    description=(
                        f"Quoted delivery date ({quoted_delivery_date.isoformat()}) exceeds the RFQ required delivery "
                        f"date ({rfq_req_date.isoformat()}) by {delay_days} calendar days."
                    ),
                    affected_field_or_item="delivery_date",
                    evidence=f"Quoted delivery: {quoted_delivery_date.isoformat()}, Required: {rfq_req_date.isoformat()}.",
                    recommended_action="Negotiate expedited production/air freight or assess late delivery liquidated damages.",
                    metadata={
                        'quoted_delivery_date': quoted_delivery_date.isoformat(),
                        'required_delivery_date': rfq_req_date.isoformat(),
                        'delay_days': delay_days,
                    },
                )
            )

    return flags


def evaluate_quantity_risks(
    rfq_items: List[Dict[str, Any]],
    quote_items: List[Dict[str, Any]],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Identifies quantity shortfall across quoted line items."""
    flags: List[RiskFlag] = []
    if not config.is_rule_enabled(RiskFlagType.QUANTITY_SHORTFALL):
        return flags

    # Build mapping of RFQ items by id or position
    rfq_map: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(rfq_items):
        item_id = str(item.get('id', ''))
        pos = item.get('position', idx + 1)
        if item_id:
            rfq_map[item_id] = item
        rfq_map[f"pos_{pos}"] = item

    for idx, q_item in enumerate(quote_items):
        item_desc = q_item.get('description') or q_item.get('item_name') or f"Line #{idx+1}"
        rfq_ref = str(q_item.get('rfq_item_id', ''))
        pos = q_item.get('position', idx + 1)

        matched_rfq = rfq_map.get(rfq_ref) or rfq_map.get(f"pos_{pos}")
        if not matched_rfq:
            continue

        req_qty = _to_decimal(matched_rfq.get('quantity'))
        quoted_qty = _to_decimal(q_item.get('quantity'))
        unit = q_item.get('unit') or matched_rfq.get('unit') or 'units'

        if req_qty > 0 and quoted_qty < req_qty:
            shortfall = req_qty - quoted_qty
            shortfall_pct = float((shortfall / req_qty) * 100)

            severity = (
                RiskSeverity.CRITICAL
                if shortfall_pct >= config.quantity_shortfall_critical_threshold_pct
                else RiskSeverity.WARNING
            )

            flags.append(
                RiskFlag(
                    type=RiskFlagType.QUANTITY_SHORTFALL,
                    severity=severity,
                    title=f"Quantity Shortfall on {item_desc} ({shortfall_pct:.1f}% deficit)",
                    description=(
                        f"Supplier quoted {quoted_qty} {unit}, which is {shortfall} {unit} ({shortfall_pct:.1f}%) "
                        f"less than the required RFQ quantity of {req_qty} {unit}."
                    ),
                    affected_field_or_item=f"items[{idx}].quantity",
                    evidence=f"Quoted: {quoted_qty} {unit}, Required: {req_qty} {unit} (Shortfall: {shortfall} {unit}).",
                    recommended_action="Check if supplier has MOQ/capacity limits or split the order with a secondary vendor.",
                    metadata={
                        'required_quantity': float(req_qty),
                        'quoted_quantity': float(quoted_qty),
                        'shortfall': float(shortfall),
                        'shortfall_percentage': round(shortfall_pct, 2),
                    },
                )
            )

    return flags


def evaluate_calculation_risks(
    quotation_data: Dict[str, Any],
    quote_items: List[Dict[str, Any]],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Performs deterministic financial math verification to catch calculation errors."""
    flags: List[RiskFlag] = []
    if not config.is_rule_enabled(RiskFlagType.CALCULATION_ERROR):
        return flags

    tol = config.calculation_rounding_tolerance
    calculated_subtotal = Decimal('0.00')

    # 1. Line Item Math
    for idx, item in enumerate(quote_items):
        item_desc = item.get('description') or item.get('item_name') or f"Line #{idx+1}"
        qty = _to_decimal(item.get('quantity'))
        unit_price = _to_decimal(item.get('unit_price'))
        disc = _to_decimal(item.get('discount'))
        tax = _to_decimal(item.get('tax'))
        stated_total = _to_decimal(item.get('line_total'))

        calc_line = (qty * unit_price) - disc + tax
        calculated_subtotal += (qty * unit_price) - disc

        line_variance = stated_total - calc_line
        if abs(line_variance) > tol:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.CALCULATION_ERROR,
                    severity=RiskSeverity.WARNING if abs(line_variance) < Decimal('1.00') else RiskSeverity.CRITICAL,
                    title=f"Line Item Arithmetic Error on {item_desc}",
                    description=(
                        f"Stated line total ({stated_total}) differs from verified calculation "
                        f"({qty} * {unit_price} - {disc} + {tax} = {calc_line}) by {line_variance}."
                    ),
                    affected_field_or_item=f"items[{idx}].line_total",
                    evidence=f"Stated: {stated_total}, Calculated: {calc_line} (Variance: {line_variance}).",
                    recommended_action="Request revised quotation correcting line item arithmetic before approval.",
                    metadata={
                        'stated_total': float(stated_total),
                        'calculated_total': float(calc_line),
                        'variance': float(line_variance),
                    },
                )
            )

    # 2. Quotation Subtotal Math
    stated_subtotal = quotation_data.get('subtotal')
    if stated_subtotal is not None:
        stated_sub = _to_decimal(stated_subtotal)
        sub_var = stated_sub - calculated_subtotal
        if abs(sub_var) > tol:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.CALCULATION_ERROR,
                    severity=RiskSeverity.WARNING if abs(sub_var) < Decimal('1.00') else RiskSeverity.CRITICAL,
                    title="Subtotal Calculation Inconsistency",
                    description=(
                        f"Stated quotation subtotal ({stated_sub}) differs from the sum of line item subtotals "
                        f"({calculated_subtotal}) by {sub_var}."
                    ),
                    affected_field_or_item="subtotal",
                    evidence=f"Stated Subtotal: {stated_sub}, Sum of Lines: {calculated_subtotal} (Variance: {sub_var}).",
                    recommended_action="Reconcile quotation subtotal with supplier line items.",
                    metadata={'stated_subtotal': float(stated_sub), 'calculated_subtotal': float(calculated_subtotal)},
                )
            )

    return flags


def evaluate_pricing_risks(
    rfq_items: List[Dict[str, Any]],
    quote_items: List[Dict[str, Any]],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """Identifies anomalous pricing such as negative prices, zero prices, or extreme price surges."""
    flags: List[RiskFlag] = []
    if not config.is_rule_enabled(RiskFlagType.PRICE_INCONSISTENCY):
        return flags

    rfq_map: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(rfq_items):
        item_id = str(item.get('id', ''))
        pos = item.get('position', idx + 1)
        if item_id:
            rfq_map[item_id] = item
        rfq_map[f"pos_{pos}"] = item

    for idx, q_item in enumerate(quote_items):
        item_desc = q_item.get('description') or q_item.get('item_name') or f"Line #{idx+1}"
        unit_price = _to_decimal(q_item.get('unit_price'))
        stated_line = _to_decimal(q_item.get('line_total'))
        qty = _to_decimal(q_item.get('quantity'))

        # Negative price
        if unit_price < 0 or stated_line < 0:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.PRICE_INCONSISTENCY,
                    severity=RiskSeverity.CRITICAL,
                    title=f"Negative Pricing on {item_desc}",
                    description=f"Line item unit price ({unit_price}) or line total ({stated_line}) is negative.",
                    affected_field_or_item=f"items[{idx}].unit_price",
                    evidence=f"Unit price: {unit_price}, Line total: {stated_line}.",
                    recommended_action="Reject corrupted quotation data or verify supplier credit note.",
                )
            )

        # Zero price on billable line
        elif unit_price == 0 and qty > 0:
            flags.append(
                RiskFlag(
                    type=RiskFlagType.PRICE_INCONSISTENCY,
                    severity=RiskSeverity.WARNING,
                    title=f"Zero Price on {item_desc}",
                    description=f"Unit price is stated as 0.00 for quantity {qty}. Ensure item is not omitted from cost.",
                    affected_field_or_item=f"items[{idx}].unit_price",
                    evidence=f"Unit price: 0.00 for quantity: {qty}.",
                    recommended_action="Clarify whether item is included gratis, FOC sample, or omitted by mistake.",
                )
            )

        # Target budget surge comparison
        rfq_ref = str(q_item.get('rfq_item_id', ''))
        pos = q_item.get('position', idx + 1)
        matched_rfq = rfq_map.get(rfq_ref) or rfq_map.get(f"pos_{pos}")
        if matched_rfq and matched_rfq.get('target_unit_price') is not None:
            target_price = _to_decimal(matched_rfq.get('target_unit_price'))
            if target_price > 0 and unit_price > 0:
                pct_surge = float(((unit_price - target_price) / target_price) * 100)
                if pct_surge >= config.price_surge_threshold_pct:
                    flags.append(
                        RiskFlag(
                            type=RiskFlagType.PRICE_INCONSISTENCY,
                            severity=RiskSeverity.WARNING,
                            title=f"Extreme Price Surge on {item_desc} (+{pct_surge:.1f}%)",
                            description=(
                                f"Quoted price of {unit_price} is {pct_surge:.1f}% higher than the internal "
                                f"budget target price of {target_price}."
                            ),
                            affected_field_or_item=f"items[{idx}].unit_price",
                            evidence=f"Quoted: {unit_price}, Target Budget: {target_price}.",
                            recommended_action="Negotiate volume discounting or solicit competitive secondary quotes.",
                            metadata={'quoted_price': float(unit_price), 'target_price': float(target_price), 'surge_pct': round(pct_surge, 2)},
                        )
                    )

    return flags


def evaluate_specification_risks(
    rfq_items: List[Dict[str, Any]],
    quote_items: List[Dict[str, Any]],
    config: RiskEngineConfig,
) -> List[RiskFlag]:
    """
    Evaluates technical specifications using deterministic rules to detect:
    - SPECIFICATION_MISMATCH
    - MISSING_SPECIFICATIONS
    """
    flags: List[RiskFlag] = []
    check_mismatch = config.is_rule_enabled(RiskFlagType.SPECIFICATION_MISMATCH)
    check_missing = config.is_rule_enabled(RiskFlagType.MISSING_SPECIFICATIONS)

    if not check_mismatch and not check_missing:
        return flags

    # Lazy import to avoid circular dependency
    from comparisons.specs import SpecificationMatchingEngine, SpecMatchStatus

    spec_engine = SpecificationMatchingEngine()

    rfq_map: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(rfq_items):
        item_id = str(item.get('id', ''))
        pos = item.get('position', idx + 1)
        if item_id:
            rfq_map[item_id] = item
        rfq_map[f"pos_{pos}"] = item

    for idx, q_item in enumerate(quote_items):
        item_desc = q_item.get('description') or q_item.get('item_name') or f"Line #{idx+1}"
        rfq_ref = str(q_item.get('rfq_item_id', ''))
        pos = q_item.get('position', idx + 1)
        matched_rfq = rfq_map.get(rfq_ref) or rfq_map.get(f"pos_{pos}")

        if not matched_rfq:
            continue

        rfq_specs = matched_rfq.get('custom_specifications') or matched_rfq.get('specifications') or {}
        quote_specs = q_item.get('specifications') or {}

        if not rfq_specs:
            continue

        summary = spec_engine.compare_item_specifications(
            rfq_item_or_specs=rfq_specs,
            supplier_item_or_specs=quote_specs,
            item_name=item_desc,
            use_ai=False,  # Strictly deterministic!
        )

        for match in summary.matches:
            # 1. Specification Mismatch
            if match.status == SpecMatchStatus.MISMATCH and check_mismatch:
                severity = RiskSeverity.CRITICAL if match.severity.value == 'critical' else RiskSeverity.WARNING
                flags.append(
                    RiskFlag(
                        type=RiskFlagType.SPECIFICATION_MISMATCH,
                        severity=severity,
                        title=f"Specification Mismatch on {item_desc}: {match.parameter_name}",
                        description=match.explanation,
                        affected_field_or_item=f"items[{idx}].specifications.{match.canonical_key}",
                        evidence=f"RFQ required '{match.requirement_value}', but supplier quoted '{match.supplier_value}'.",
                        recommended_action="Request revised quotation with compliant specifications or obtain engineering sign-off.",
                        metadata={
                            'parameter_name': match.parameter_name,
                            'required_value': match.requirement_value,
                            'quoted_value': match.supplier_value,
                        },
                    )
                )

            # 2. Missing Specifications
            elif match.status == SpecMatchStatus.MISSING and check_missing:
                severity = RiskSeverity.CRITICAL if match.severity.value == 'critical' else RiskSeverity.WARNING
                flags.append(
                    RiskFlag(
                        type=RiskFlagType.MISSING_SPECIFICATIONS,
                        severity=severity,
                        title=f"Missing Specification on {item_desc}: {match.parameter_name}",
                        description=f"Specification '{match.parameter_name}' was requested in the RFQ but omitted from the quote.",
                        affected_field_or_item=f"items[{idx}].specifications.{match.canonical_key}",
                        evidence=f"RFQ required '{match.requirement_value}', but supplier omitted parameter.",
                        recommended_action="Require vendor to confirm compliance with this specification in writing.",
                        metadata={'parameter_name': match.parameter_name, 'required_value': match.requirement_value},
                    )
                )

    return flags
