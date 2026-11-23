"""
Deterministic Calculation Formulas for Explainable Supplier Scoring.
Every score has a verifiable mathematical formula, transparent inputs, and clear prose explanation.
"""
from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Dict, Optional, Tuple

from comparisons.risk.evaluators import (
    check_warranty_disclaimer,
    extract_advance_payment_percentage,
)


def _to_date(val: Any) -> Optional[date]:
    """Helper to safely coerce str, datetime, or date into a datetime.date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val.strip()[:10])
        except Exception:
            return None
    return None


def _to_decimal(val: Any) -> Optional[Decimal]:
    """Helper to safely coerce numeric values or strings into Decimal."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return None


def calculate_price_score(
    quoted_price: Optional[Decimal],
    lowest_price: Optional[Decimal],
    currency: str = 'USD',
    target_budget_price: Optional[Decimal] = None,
) -> Tuple[float, Optional[float], str, str]:
    """
    Computes Price Competitiveness score (0.0 to 100.0) using relative financial efficiency:
        Price Score = (Lowest Comparable Price / Quoted Price) * 100.0

    Returns: (normalized_score, raw_metric, formula_str, explanation)
    """
    quoted_price = _to_decimal(quoted_price)
    lowest_price = _to_decimal(lowest_price)
    target_budget_price = _to_decimal(target_budget_price)

    if quoted_price is None or quoted_price <= Decimal('0.00'):
        return (
            0.0,
            None,
            "Price is missing or <= 0.00 -> Score = 0.00",
            "Quotation price is missing, zero, or negative; cannot be evaluated for competitiveness.",
        )

    # Use lowest_price as benchmark; fall back to target_budget_price if only 1 quote exists
    benchmark_price = lowest_price if (lowest_price and lowest_price > Decimal('0.00')) else target_budget_price

    if not benchmark_price or benchmark_price <= Decimal('0.00'):
        # Single quotation with no baseline
        return (
            100.0,
            float(quoted_price),
            f"Quoted {quoted_price:.2f} {currency} (No alternative benchmark available) -> Score = 100.00",
            f"Quotation of {quoted_price:.2f} {currency} is the sole benchmark available; assigned baseline score 100.00.",
        )

    # Compute ratio
    ratio = float(benchmark_price / quoted_price)
    score = min(100.0, max(0.0, ratio * 100.0))

    formula_str = f"({benchmark_price:.2f} {currency} [Lowest] / {quoted_price:.2f} {currency} [Quoted]) * 100 = {score:.2f}"

    if quoted_price == benchmark_price:
        explanation = f"Lowest comparable price ({quoted_price:.2f} {currency}); awarded maximum score of 100.00."
    else:
        variance_pct = ((quoted_price - benchmark_price) / benchmark_price) * Decimal('100.0')
        explanation = (
            f"Quoted price ({quoted_price:.2f} {currency}) is {float(variance_pct):.1f}% higher than the "
            f"lowest bid ({benchmark_price:.2f} {currency}), resulting in a relative score of {score:.2f}."
        )

    return (round(score, 2), float(quoted_price), formula_str, explanation)


def calculate_spec_score(
    spec_match_score: float,
    has_critical_mismatches: bool = False,
    mismatches_count: int = 0,
    missing_count: int = 0,
    total_requirements: int = 0,
) -> Tuple[float, float, str, str]:
    """
    Computes Specification Compliance score (0.0 to 100.0).
    Critical discrepancies (e.g. NPN vs PNP polarity, AC vs DC) set the score to 0.0.

    Returns: (normalized_score, raw_metric, formula_str, explanation)
    """
    if has_critical_mismatches:
        formula_str = f"Spec Match ({spec_match_score:.1f}%) overridden to 0.00 due to Critical Mismatches ({mismatches_count})"
        explanation = (
            f"Supplier has {mismatches_count} critical specification mismatch(es) (e.g. polarity, voltage, or dimensions). "
            "Because mandatory engineering requirements are violated, the specification score is 0.00."
        )
        return (0.0, round(spec_match_score, 2), formula_str, explanation)

    # Standard linear score
    score = min(100.0, max(0.0, spec_match_score))
    formula_str = f"Deterministic Spec Match Score: {score:.2f}%"

    if score >= 100.0:
        explanation = "100% compliance with all requested technical specifications."
    elif score >= 80.0:
        explanation = f"High specification compliance ({score:.1f}%); minor non-critical variances noted."
    elif score >= 50.0:
        explanation = f"Moderate specification compliance ({score:.1f}%); multiple parameters require engineering review."
    else:
        explanation = f"Low specification compliance ({score:.1f}%); significant technical variance from RFQ requirements."

    return (round(score, 2), round(spec_match_score, 2), formula_str, explanation)


def calculate_delivery_score(
    quoted_delivery_date: Optional[Any] = None,
    required_delivery_date: Optional[Any] = None,
    quoted_lead_time_weeks: Optional[float] = None,
    fastest_lead_time_weeks: Optional[float] = None,
) -> Tuple[float, Optional[float], str, str]:
    """
    Computes Delivery & Schedule score (0.0 to 100.0).
    On-time delivery yields 100.0; delays are penalized at 3.0 points per calendar day.

    Returns: (normalized_score, raw_metric, formula_str, explanation)
    """
    quoted_delivery_date = _to_date(quoted_delivery_date)
    required_delivery_date = _to_date(required_delivery_date)

    # 1. Date-based comparison (Preferred)
    if quoted_delivery_date and required_delivery_date:
        if quoted_delivery_date <= required_delivery_date:
            days_early = (required_delivery_date - quoted_delivery_date).days
            early_text = f" ({days_early} days early)" if days_early > 0 else " (Exact target date)"
            formula_str = f"Quoted ({quoted_delivery_date}) <= Required ({required_delivery_date}) -> Score = 100.00"
            explanation = f"Delivery schedule meets required project deadline{early_text}."
            return (100.0, 0.0, formula_str, explanation)
        else:
            delay_days = (quoted_delivery_date - required_delivery_date).days
            penalty_per_day = 3.0
            score = max(0.0, 100.0 - (delay_days * penalty_per_day))
            formula_str = f"100.00 - ({delay_days} delay days * {penalty_per_day:.1f}) = {score:.2f}"
            explanation = (
                f"Quoted delivery ({quoted_delivery_date}) is {delay_days} days late relative to the RFQ deadline "
                f"({required_delivery_date}), resulting in a penalized score of {score:.2f}."
            )
            return (round(score, 2), float(delay_days), formula_str, explanation)

    # 2. Lead-time-based comparison (Fallback)
    if quoted_lead_time_weeks is not None and quoted_lead_time_weeks > 0:
        if fastest_lead_time_weeks and fastest_lead_time_weeks > 0:
            ratio = fastest_lead_time_weeks / quoted_lead_time_weeks
            score = min(100.0, max(0.0, ratio * 100.0))
            formula_str = f"({fastest_lead_time_weeks:.1f} wks [Fastest] / {quoted_lead_time_weeks:.1f} wks [Quoted]) * 100 = {score:.2f}"
            explanation = (
                f"Quoted lead time of {quoted_lead_time_weeks:.1f} weeks compared against fastest benchmark "
                f"({fastest_lead_time_weeks:.1f} weeks); awarded {score:.2f}."
            )
            return (round(score, 2), float(quoted_lead_time_weeks), formula_str, explanation)
        else:
            # Baseline lead time: <= 2 weeks is 100, > 12 weeks is 20
            if quoted_lead_time_weeks <= 2.0:
                score = 100.0
            elif quoted_lead_time_weeks <= 4.0:
                score = 85.0
            elif quoted_lead_time_weeks <= 8.0:
                score = 65.0
            elif quoted_lead_time_weeks <= 12.0:
                score = 45.0
            else:
                score = 20.0
            formula_str = f"Standard Lead Time Tier ({quoted_lead_time_weeks:.1f} weeks) -> Score = {score:.2f}"
            explanation = f"Quoted lead time of {quoted_lead_time_weeks:.1f} weeks falls into tier score {score:.2f}."
            return (round(score, 2), float(quoted_lead_time_weeks), formula_str, explanation)

    # Missing delivery schedule
    return (
        30.0,
        None,
        "No delivery schedule or lead time stated -> Score = 30.00",
        "Quotation omitted delivery schedule and lead time; assigned default penalty score 30.00.",
    )


def calculate_payment_score(payment_terms: str) -> Tuple[float, Optional[float], str, str]:
    """
    Computes Payment Terms score (0.0 to 100.0) evaluating working capital advantage:
    Extended credit (Net 60/90) = 100; Standard (Net 30) = 85; 100% Advance/COD = 0.

    Returns: (normalized_score, raw_metric, formula_str, explanation)
    """
    if not payment_terms or not payment_terms.strip():
        return (
            40.0,
            None,
            "Unspecified payment terms -> Score = 40.00",
            "Payment terms are missing or unstated; assigned baseline unverified score 40.00.",
        )

    clean = payment_terms.lower().strip()

    # 1. Advance payment percentage penalty
    advance_pct = extract_advance_payment_percentage(payment_terms)
    if advance_pct is not None:
        if advance_pct >= 100.0:
            return (
                0.0,
                100.0,
                "100% Advance Payment Required -> Score = 0.00",
                "Full advance payment shifts complete performance and credit risk to the buyer; awarded 0.00.",
            )
        elif advance_pct >= 50.0:
            score = 20.0
            return (
                score,
                advance_pct,
                f"{advance_pct:.0f}% Advance Payment Required -> Score = {score:.2f}",
                f"High advance payment requirement ({advance_pct:.0f}%) creates significant cash flow exposure; awarded {score:.2f}.",
            )
        elif advance_pct >= 30.0:
            score = 35.0
            return (
                score,
                advance_pct,
                f"{advance_pct:.0f}% Advance Payment Required -> Score = {score:.2f}",
                f"Moderate advance payment requirement ({advance_pct:.0f}%); awarded {score:.2f}.",
            )
        elif advance_pct > 0:
            score = 50.0
            return (
                score,
                advance_pct,
                f"{advance_pct:.0f}% Advance Payment Required -> Score = {score:.2f}",
                f"Minor deposit requirement ({advance_pct:.0f}%); awarded {score:.2f}.",
            )

    # 2. Credit Terms (Net X Days)
    net_match = re.search(r'net\s*(\d+)', clean)
    if net_match:
        days = int(net_match.group(1))
        if days >= 60:
            score = 100.0
            desc = "Extended commercial credit (Net 60+ days) offers optimal working capital flexibility."
        elif days >= 45:
            score = 92.0
            desc = f"Favorable commercial credit (Net {days} days)."
        elif days >= 30:
            score = 85.0
            desc = f"Standard procurement credit terms (Net {days} days)."
        elif days >= 15:
            score = 70.0
            desc = f"Short credit terms (Net {days} days)."
        else:
            score = 55.0
            desc = f"Very short credit window (Net {days} days)."

        formula_str = f"Credit Terms (Net {days} days) -> Score = {score:.2f}"
        return (score, float(days), formula_str, desc)

    # 3. Known commercial terms
    if 'cod' in clean or 'cash on delivery' in clean:
        return (
            10.0,
            0.0,
            "Cash on Delivery (COD) -> Score = 10.00",
            "COD requires immediate disbursement upon arrival without prior quality inspection.",
        )
    if 'milestone' in clean or 'progress' in clean:
        return (
            65.0,
            None,
            "Milestone / Progress Payments -> Score = 65.00",
            "Milestone payments tied to verified delivery deliverables.",
        )

    # General terms fallback
    return (
        50.0,
        None,
        f"Non-standard Payment Terms: '{payment_terms}' -> Score = 50.00",
        f"Non-standard terms '{payment_terms}' evaluated as neutral commercial terms.",
    )


def calculate_warranty_score(warranty_text: str) -> Tuple[float, Optional[float], str, str]:
    """
    Computes Warranty Coverage score (0.0 to 100.0).
    3+ years = 100; 2 years = 95; 1 year = 80; <6 months = 25; No warranty = 0.

    Returns: (normalized_score, raw_metric, formula_str, explanation)
    """
    if not warranty_text or not warranty_text.strip():
        return (
            15.0,
            None,
            "Unspecified Warranty Terms -> Score = 15.00",
            "Warranty coverage is unstated; assigned default unverified score 15.00.",
        )

    clean = warranty_text.lower().strip()

    # 1. Explicit disclaimer
    if check_warranty_disclaimer(warranty_text):
        return (
            0.0,
            0.0,
            "Explicit Warranty Disclaimer ('as-is') -> Score = 0.00",
            "Supplier explicitly disclaims warranty coverage; awarded 0.00.",
        )

    # 2. Extract months or years
    # Years pattern: e.g. "2 years", "3 yr warranty"
    yr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|yr)', clean)
    if yr_match:
        try:
            years = float(yr_match.group(1))
            months = years * 12.0
        except ValueError:
            months = 12.0
    else:
        # Months pattern: e.g. "24 months", "18 mo"
        mo_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:month|mo)', clean)
        if mo_match:
            try:
                months = float(mo_match.group(1))
            except ValueError:
                months = 12.0
        else:
            months = None

    if months is not None:
        if months >= 36.0:
            score = 100.0
            desc = f"Exceptional warranty protection ({months:.0f} months / {months/12:.1f} years)."
        elif months >= 24.0:
            score = 95.0
            desc = f"Extended 2-year warranty coverage ({months:.0f} months)."
        elif months >= 12.0:
            score = 80.0
            desc = f"Standard 1-year commercial warranty ({months:.0f} months)."
        elif months >= 6.0:
            score = 50.0
            desc = f"Limited warranty protection ({months:.0f} months)."
        else:
            score = 25.0
            desc = f"Very short warranty duration ({months:.0f} months)."

        formula_str = f"Warranty Duration: {months:.0f} months -> Score = {score:.2f}"
        return (score, float(months), formula_str, desc)

    # General stated warranty without numeric duration
    if 'lifetime' in clean:
        return (100.0, None, "Lifetime Warranty -> Score = 100.00", "Manufacturer lifetime warranty coverage.")
    if 'standard' in clean or 'manufacturer' in clean or 'oem' in clean:
        return (75.0, 12.0, "Standard OEM Warranty -> Score = 75.00", "Standard manufacturer warranty coverage.")

    return (
        60.0,
        None,
        f"Stated Warranty: '{warranty_text}' -> Score = 60.00",
        f"Quoted warranty terms '{warranty_text}' acknowledged.",
    )
