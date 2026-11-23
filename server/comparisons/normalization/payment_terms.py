"""
Payment Terms Normalization and Financial Risk Engine.
Deterministically classifies payment structures:
- Advance payment vs Credit payment terms (e.g. "100% Advance" vs "Net 30 Days").
- Split milestone payments (e.g. "30% Advance, 70% against BL").
- Cash on Delivery (COD) and Letters of Credit (LC).
- Evaluates working capital burden and cash flow exposure.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import re
from typing import List, Optional, Tuple


class PaymentTermCategory(str, Enum):
    ADVANCE = 'ADVANCE'                  # 100% advance payment required before production/dispatch
    NET_CREDIT = 'NET_CREDIT'            # Standard post-invoice credit (Net 15, 30, 45, 60, 90)
    PARTIAL_ADVANCE = 'PARTIAL_ADVANCE'  # Split terms: advance + credit/dispatch
    COD = 'COD'                          # Cash on delivery / Payment upon receipt
    LETTER_OF_CREDIT = 'LETTER_OF_CREDIT'# L/C at sight or Usance L/C
    MILESTONE = 'MILESTONE'              # Progress billing based on engineering milestones
    OTHER = 'OTHER'                      # Custom / Unclassified commercial clause


@dataclass
class PaymentMilestone:
    stage: str
    percent: Decimal
    days_offset: int = 0


@dataclass
class NormalizedPaymentTerms:
    raw_text: str
    category: PaymentTermCategory
    advance_percent: Decimal
    credit_percent: Decimal
    credit_days: int                     # e.g. 30 for Net 30, 60 for Net 60
    has_advance_requirement: bool
    cash_flow_risk_score: Decimal        # 1.0 (Most buyer-friendly) to 10.0 (High buyer working capital burden)
    milestones: List[PaymentMilestone]
    summary: str


def normalize_payment_terms(raw_terms: Optional[str]) -> NormalizedPaymentTerms:
    """
    Deterministically parses and normalizes commercial payment terms.
    Examples:
        - "100% advance" -> ADVANCE, advance=100%, credit_days=0, risk=10.0
        - "Net 30 Days" -> NET_CREDIT, advance=0%, credit_days=30, risk=3.0
        - "Net 60" -> NET_CREDIT, advance=0%, credit_days=60, risk=1.5
        - "30% advance, 70% against dispatch" -> PARTIAL_ADVANCE, advance=30%, credit=70%, risk=5.5
        - "Cash on Delivery" -> COD, advance=0%, credit_days=0, risk=4.0
        - "LC at sight" -> LETTER_OF_CREDIT, advance=0%, credit_days=0, risk=5.0
    """
    if not raw_terms or not raw_terms.strip():
        return NormalizedPaymentTerms(
            raw_text='',
            category=PaymentTermCategory.OTHER,
            advance_percent=Decimal('0.0'),
            credit_percent=Decimal('0.0'),
            credit_days=0,
            has_advance_requirement=False,
            cash_flow_risk_score=Decimal('5.0'),
            milestones=[],
            summary='Unspecified payment terms',
        )

    text = raw_terms.strip()
    lower = text.lower()

    # 1. Check for 100% Advance / Full Advance
    if (
        '100% advance' in lower or
        '100 % advance' in lower or
        'full advance' in lower or
        'advance payment before dispatch' in lower or
        'payment in advance' in lower or
        'prepayment' in lower or
        (re.search(r'\b100\s*%\s*(?:in\s+)?advance\b', lower))
    ):
        return NormalizedPaymentTerms(
            raw_text=text,
            category=PaymentTermCategory.ADVANCE,
            advance_percent=Decimal('100.0'),
            credit_percent=Decimal('0.0'),
            credit_days=0,
            has_advance_requirement=True,
            cash_flow_risk_score=Decimal('10.0'),
            milestones=[PaymentMilestone(stage='Full Prepayment', percent=Decimal('100.0'), days_offset=0)],
            summary='100% Advance Payment (Immediate Cash Outflow)',
        )

    # 2. Check for Split Advance (e.g. "30% advance, 70% against BL/dispatch/delivery")
    split_pattern = re.search(
        r'(\d+)\s*%\s*(?:in\s+)?advance(?:.*?(\d+)\s*%\s*(?:on|against|upon|after|before)?\s*(delivery|dispatch|bl|b/l|shipment|invoice|completion))?',
        lower
    )
    if split_pattern:
        advance_pct = Decimal(split_pattern.group(1))
        second_pct = Decimal(split_pattern.group(2)) if split_pattern.group(2) else (Decimal('100.0') - advance_pct)
        second_stage = split_pattern.group(3) or 'delivery/dispatch'

        # Risk score: 0% advance -> 2.0; 100% advance -> 10.0
        risk = (Decimal('2.0') + (advance_pct * Decimal('0.08'))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        # Check if second portion has credit days (e.g. 70% Net 30)
        net_in_split = re.search(r'net\s*(\d+)', lower)
        credit_days = int(net_in_split.group(1)) if net_in_split else 0

        return NormalizedPaymentTerms(
            raw_text=text,
            category=PaymentTermCategory.PARTIAL_ADVANCE,
            advance_percent=advance_pct,
            credit_percent=second_pct,
            credit_days=credit_days,
            has_advance_requirement=True,
            cash_flow_risk_score=risk,
            milestones=[
                PaymentMilestone(stage='Advance with Order', percent=advance_pct, days_offset=0),
                PaymentMilestone(stage=f"Balance upon {second_stage}", percent=second_pct, days_offset=credit_days),
            ],
            summary=f"{advance_pct}% Advance, {second_pct}% on {second_stage.upper()}",
        )

    # 3. Check for Net Credit Terms (e.g. "Net 30", "Net 60 Days", "30 days net", "45 days from invoice")
    net_match = re.search(r'(?:net\s*(\d+)|(\d+)\s*days\s*net|(\d+)\s*days\s*from\s*(?:invoice|receipt|delivery))', lower)
    if net_match:
        days_str = net_match.group(1) or net_match.group(2) or net_match.group(3)
        credit_days = int(days_str)

        # Risk score decreases as credit days increase (buyer friendly)
        # Net 15 -> 4.5, Net 30 -> 3.0, Net 60 -> 1.5, Net 90 -> 1.0
        if credit_days >= 90:
            risk = Decimal('1.0')
        elif credit_days >= 60:
            risk = Decimal('1.5')
        elif credit_days >= 45:
            risk = Decimal('2.0')
        elif credit_days >= 30:
            risk = Decimal('3.0')
        else:
            risk = Decimal('4.5')

        return NormalizedPaymentTerms(
            raw_text=text,
            category=PaymentTermCategory.NET_CREDIT,
            advance_percent=Decimal('0.0'),
            credit_percent=Decimal('100.0'),
            credit_days=credit_days,
            has_advance_requirement=False,
            cash_flow_risk_score=risk,
            milestones=[PaymentMilestone(stage=f"Net {credit_days} Days Credit", percent=Decimal('100.0'), days_offset=credit_days)],
            summary=f"Net {credit_days} Days Credit (Buyer Friendly)",
        )

    # 4. Check for COD / Cash On Delivery
    if 'cod' in lower or 'cash on delivery' in lower or 'payment on delivery' in lower or 'pod' in lower:
        return NormalizedPaymentTerms(
            raw_text=text,
            category=PaymentTermCategory.COD,
            advance_percent=Decimal('0.0'),
            credit_percent=Decimal('100.0'),
            credit_days=0,
            has_advance_requirement=False,
            cash_flow_risk_score=Decimal('4.0'),
            milestones=[PaymentMilestone(stage='Cash on Delivery', percent=Decimal('100.0'), days_offset=0)],
            summary='Cash on Delivery (Payment at Receipt)',
        )

    # 5. Check for Letter of Credit (LC)
    if 'lc' in lower or 'letter of credit' in lower or 'l/c' in lower:
        lc_days = 0
        usance_match = re.search(r'(?:lc|l/c)\s*(\d+)\s*days', lower)
        if usance_match:
            lc_days = int(usance_match.group(1))

        return NormalizedPaymentTerms(
            raw_text=text,
            category=PaymentTermCategory.LETTER_OF_CREDIT,
            advance_percent=Decimal('0.0'),
            credit_percent=Decimal('100.0'),
            credit_days=lc_days,
            has_advance_requirement=False,
            cash_flow_risk_score=Decimal('4.5') if lc_days > 0 else Decimal('5.0'),
            milestones=[PaymentMilestone(stage=f"Letter of Credit ({'Sight' if lc_days == 0 else f'{lc_days} Days'})", percent=Decimal('100.0'), days_offset=lc_days)],
            summary=f"Letter of Credit ({'At Sight' if lc_days == 0 else f'{lc_days} Days Usance'})",
        )

    # 6. Fallback generic payment terms
    return NormalizedPaymentTerms(
        raw_text=text,
        category=PaymentTermCategory.OTHER,
        advance_percent=Decimal('0.0'),
        credit_percent=Decimal('100.0'),
        credit_days=0,
        has_advance_requirement=False,
        cash_flow_risk_score=Decimal('5.0'),
        milestones=[PaymentMilestone(stage=text, percent=Decimal('100.0'), days_offset=0)],
        summary=text[:60],
    )
