"""
Lead Time and Delivery Schedule Normalization Engine.
Deterministically standardizes delivery timelines across days, weeks, months,
ex-stock declarations, and ranges (e.g. "14 days", "2 weeks", "3-4 weeks ARO", "ex-stock").
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Optional, Tuple


@dataclass
class NormalizedLeadTime:
    raw_text: str
    min_days: int
    max_days: int
    representative_days: int   # Conservative planning timeline (max_days)
    lead_time_weeks: Decimal    # Standard normalized weeks (days / 7.0)
    is_ex_stock: bool
    is_range: bool
    trigger_condition: Optional[str] = None  # e.g. "After Receipt of Order (ARO)"


def normalize_lead_time(raw_lead_time: Optional[str]) -> NormalizedLeadTime:
    """
    Parses and deterministically normalizes arbitrary lead time strings.
    Handles:
        - "14 days" -> 14 days, 2.0 weeks
        - "2 weeks" -> 14 days, 2.0 weeks
        - "3 to 4 weeks" -> min: 21 days, max: 28 days, weeks: 4.0
        - "1 month" -> 30 days, 4.3 weeks
        - "ex-stock" / "immediate" / "ready" -> 0-2 days, 0.0 weeks, is_ex_stock=True
        - "10 business days" / "10 working days" -> 14 calendar days (10 * 7 / 5)
    """
    if not raw_lead_time or not raw_lead_time.strip():
        return NormalizedLeadTime(
            raw_text='',
            min_days=0,
            max_days=0,
            representative_days=0,
            lead_time_weeks=Decimal('0.0'),
            is_ex_stock=False,
            is_range=False,
            trigger_condition=None,
        )

    text = raw_lead_time.strip()
    lower = text.lower()

    # 1. Check for immediate / ex-stock / ready in stock
    if any(k in lower for k in ('ex-stock', 'ex stock', 'in stock', 'immediate', 'ready stock', 'ready in stock', 'off-the-shelf')):
        return NormalizedLeadTime(
            raw_text=text,
            min_days=0,
            max_days=2,
            representative_days=2,
            lead_time_weeks=Decimal('0.3'),
            is_ex_stock=True,
            is_range=False,
            trigger_condition='Ex-Stock Dispatch',
        )

    # 2. Extract trigger condition (e.g. ARO, PO, Advance)
    trigger = None
    if 'aro' in lower or 'receipt of order' in lower or 'po' in lower:
        trigger = 'After Receipt of Order (ARO)'
    elif 'advance' in lower or 'down payment' in lower:
        trigger = 'After Receipt of Advance Payment'
    elif 'drawing' in lower or 'approval' in lower:
        trigger = 'After Drawing Approval'

    # 3. Detect Business Days vs Calendar Days
    is_business_days = 'business day' in lower or 'working day' in lower

    # 4. Range patterns: "X to Y [unit]" or "X - Y [unit]" or "X-Y [unit]"
    range_pattern = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:-|to|\.\.)\s*(\d+(?:\.\d+)?)\s*(?:business|working|calendar)?\s*(day|days|wk|wks|week|weeks|mo|mos|month|months|hour|hours|hr|hrs)?',
        lower
    )

    if range_pattern:
        min_val = float(range_pattern.group(1))
        max_val = float(range_pattern.group(2))
        unit_str = range_pattern.group(3) or ''

        # If unit wasn't attached directly to range, look anywhere in the text
        if not unit_str:
            if 'week' in lower or 'wk' in lower:
                unit_str = 'week'
            elif 'month' in lower or 'mo' in lower:
                unit_str = 'month'
            elif 'hour' in lower or 'hr' in lower:
                unit_str = 'hour'
            else:
                unit_str = 'day'

        multiplier = _get_day_multiplier(unit_str, is_business_days)
        min_days = int(round(min_val * multiplier))
        max_days = int(round(max_val * multiplier))
        rep_days = max_days  # Procurement standard: plan for worst-case supplier delivery
        weeks = (Decimal(str(rep_days)) / Decimal('7.0')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        return NormalizedLeadTime(
            raw_text=text,
            min_days=min_days,
            max_days=max_days,
            representative_days=rep_days,
            lead_time_weeks=weeks,
            is_ex_stock=False,
            is_range=True,
            trigger_condition=trigger,
        )

    # 5. Single value pattern: "X [unit]" (including "X business days", "X working days", "X hours")
    single_pattern = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:business|working|calendar)?\s*(day|days|wk|wks|week|weeks|mo|mos|month|months|hour|hours|hr|hrs)',
        lower
    )

    if single_pattern:
        val = float(single_pattern.group(1))
        unit_str = single_pattern.group(2)
        multiplier = _get_day_multiplier(unit_str, is_business_days)
        days = int(round(val * multiplier))
        weeks = (Decimal(str(days)) / Decimal('7.0')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        return NormalizedLeadTime(
            raw_text=text,
            min_days=days,
            max_days=days,
            representative_days=days,
            lead_time_weeks=weeks,
            is_ex_stock=False,
            is_range=False,
            trigger_condition=trigger,
        )

    # 6. Fallback: single number with default interpretation as weeks (standard procurement practice) or days
    num_match = re.search(r'(\d+(?:\.\d+)?)', lower)
    if num_match:
        val = float(num_match.group(1))
        # If val <= 12, assume weeks; if > 12, assume calendar days
        if val <= 12:
            days = int(round(val * 7))
            weeks = Decimal(str(val)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        else:
            days = int(round(val))
            weeks = (Decimal(str(days)) / Decimal('7.0')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        return NormalizedLeadTime(
            raw_text=text,
            min_days=days,
            max_days=days,
            representative_days=days,
            lead_time_weeks=weeks,
            is_ex_stock=False,
            is_range=False,
            trigger_condition=trigger,
        )

    # Unparseable text fallback
    return NormalizedLeadTime(
        raw_text=text,
        min_days=0,
        max_days=0,
        representative_days=0,
        lead_time_weeks=Decimal('0.0'),
        is_ex_stock=False,
        is_range=False,
        trigger_condition=trigger,
    )


def _get_day_multiplier(unit_str: str, is_business_days: bool = False) -> float:
    unit = unit_str.lower().strip()
    if 'hour' in unit or 'hr' in unit:
        return 1.0 / 24.0
    if 'week' in unit or 'wk' in unit:
        return 7.0
    if 'month' in unit or 'mo' in unit:
        return 30.0
    if is_business_days:
        # 5 business days = 7 calendar days
        return 7.0 / 5.0
    return 1.0
