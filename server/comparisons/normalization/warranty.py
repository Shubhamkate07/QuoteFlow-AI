"""
Warranty Terms Normalization Engine.
Deterministically normalizes warranty coverage across durations (days, months, years),
coverage types (manufacturer vs seller direct, parts only, comprehensive), and disclaimers.
"""
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional


class WarrantyType(str, Enum):
    MANUFACTURER = 'MANUFACTURER'        # OEM / Manufacturer warranty
    SELLER_DIRECT = 'SELLER_DIRECT'      # Direct vendor / distributor warranty
    COMPREHENSIVE = 'COMPREHENSIVE'      # Full parts and labor coverage
    PARTS_ONLY = 'PARTS_ONLY'            # Parts only / excludes labor
    LIMITED = 'LIMITED'                  # Standard limited liability warranty
    LIFETIME = 'LIFETIME'                # Lifetime product guarantee
    NO_WARRANTY = 'NO_WARRANTY'          # Sold as-is / No commercial warranty
    OTHER = 'OTHER'                      # Custom warranty agreement


@dataclass
class NormalizedWarranty:
    raw_text: str
    duration_months: int
    duration_days: int
    warranty_type: WarrantyType
    is_covered: bool
    summary: str
    coverage_conditions: Optional[str] = None


def normalize_warranty(raw_warranty: Optional[str]) -> NormalizedWarranty:
    """
    Parses and deterministically normalizes warranty duration and terms.
    Examples:
        - "1 year" -> 12 months, 365 days, LIMITED, is_covered=True
        - "12 months" -> 12 months, 365 days, LIMITED, is_covered=True
        - "24 months manufacturer warranty" -> 24 months, 730 days, MANUFACTURER, is_covered=True
        - "3 years comprehensive" -> 36 months, 1095 days, COMPREHENSIVE, is_covered=True
        - "90 days" -> 3 months, 90 days, LIMITED, is_covered=True
        - "lifetime" -> 999 months, 36500 days, LIFETIME, is_covered=True
        - "None" / "As-Is" / "No warranty" -> 0 months, 0 days, NO_WARRANTY, is_covered=False
    """
    if not raw_warranty or not raw_warranty.strip():
        return NormalizedWarranty(
            raw_text='',
            duration_months=0,
            duration_days=0,
            warranty_type=WarrantyType.NO_WARRANTY,
            is_covered=False,
            summary='No warranty information stated',
            coverage_conditions=None,
        )

    text = raw_warranty.strip()
    lower = text.lower()

    # 1. Check for explicit "No warranty" / "As-is" / "None"
    if any(k in lower for k in ('no warranty', 'without warranty', 'none', 'as-is', 'as is', 'not applicable', 'n/a')):
        return NormalizedWarranty(
            raw_text=text,
            duration_months=0,
            duration_days=0,
            warranty_type=WarrantyType.NO_WARRANTY,
            is_covered=False,
            summary='No Warranty Provided (As-Is)',
            coverage_conditions=None,
        )

    # 2. Check for Lifetime Warranty
    if 'lifetime' in lower:
        return NormalizedWarranty(
            raw_text=text,
            duration_months=999,
            duration_days=36500,
            warranty_type=WarrantyType.LIFETIME,
            is_covered=True,
            summary='Lifetime Product Warranty',
            coverage_conditions='Subject to normal operational use',
        )

    # 3. Determine Warranty Type
    w_type = WarrantyType.LIMITED
    if 'manufacturer' in lower or 'oem' in lower:
        w_type = WarrantyType.MANUFACTURER
    elif 'comprehensive' in lower or 'full' in lower:
        w_type = WarrantyType.COMPREHENSIVE
    elif 'parts only' in lower or 'parts-only' in lower:
        w_type = WarrantyType.PARTS_ONLY
    elif 'seller' in lower or 'vendor' in lower:
        w_type = WarrantyType.SELLER_DIRECT

    # 4. Check for complex dual-condition clauses:
    # e.g. "18 months from supply or 12 months from commissioning"
    dual_match = re.search(
        r'(\d+)\s*(?:months?|mos?)\s*(?:from|after)?\s*(?:supply|dispatch|delivery).*?(?:or|\/)\s*(\d+)\s*(?:months?|mos?)\s*(?:from|after)?\s*(?:commissioning|installation)',
        lower
    )
    if dual_match:
        supply_months = int(dual_match.group(1))
        comm_months = int(dual_match.group(2))
        # Use commissioning duration as standard benchmark
        months = comm_months
        days = months * 30
        return NormalizedWarranty(
            raw_text=text,
            duration_months=months,
            duration_days=days,
            warranty_type=w_type,
            is_covered=True,
            summary=f"{months} Months from Commissioning ({supply_months} Months from Supply)",
            coverage_conditions=f"{supply_months} months from dispatch / {comm_months} months from commissioning, whichever earlier",
        )

    # 5. Year-based durations: "X year(s)" / "X yr(s)"
    year_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|years|yr|yrs)', lower)
    if year_match:
        years = float(year_match.group(1))
        months = int(round(years * 12))
        days = int(round(years * 365))
        return NormalizedWarranty(
            raw_text=text,
            duration_months=months,
            duration_days=days,
            warranty_type=w_type,
            is_covered=True,
            summary=f"{months} Months ({years:g} Year{'s' if years != 1 else ''}) Warranty",
            coverage_conditions=None,
        )

    # 6. Month-based durations: "X month(s)" / "X mo(s)"
    month_match = re.search(r'(\d+)\s*(?:month|months|mo|mos)', lower)
    if month_match:
        months = int(month_match.group(1))
        days = (months // 12) * 365 if months % 12 == 0 else months * 30
        return NormalizedWarranty(
            raw_text=text,
            duration_months=months,
            duration_days=days,
            warranty_type=w_type,
            is_covered=True,
            summary=f"{months} Months Warranty",
            coverage_conditions=None,
        )

    # 7. Day-based durations: "X day(s)"
    day_match = re.search(r'(\d+)\s*(?:day|days)', lower)
    if day_match:
        days = int(day_match.group(1))
        months = max(1, int(round(days / 30)))
        return NormalizedWarranty(
            raw_text=text,
            duration_months=months,
            duration_days=days,
            warranty_type=w_type,
            is_covered=True,
            summary=f"{days} Days ({months} Mo) Limited Warranty",
            coverage_conditions=None,
        )

    # 8. Lone number fallback (assume months if <= 36, days if > 36)
    lone_num = re.search(r'(\d+)', lower)
    if lone_num:
        val = int(lone_num.group(1))
        if val <= 36:
            months = val
            days = months * 30
        else:
            days = val
            months = max(1, int(round(days / 30)))
        return NormalizedWarranty(
            raw_text=text,
            duration_months=months,
            duration_days=days,
            warranty_type=w_type,
            is_covered=True,
            summary=f"{months} Months Standard Warranty",
            coverage_conditions=None,
        )

    # Fallback with raw text
    return NormalizedWarranty(
        raw_text=text,
        duration_months=12,  # Commercial default
        duration_days=365,
        warranty_type=WarrantyType.LIMITED,
        is_covered=True,
        summary=text[:60],
        coverage_conditions=None,
    )
