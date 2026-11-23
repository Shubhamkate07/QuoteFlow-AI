"""
Tax and Discount Normalization Engine.
Deterministically reconciles:
- Percent tax vs Fixed tax amounts (e.g. 18% GST vs $150.00 fixed tax).
- Tax-inclusive vs Tax-exclusive pricing structures.
- Percent discounts vs Fixed lump-sum discounts.
- Line-item level discounts vs Document-level commercial discounts.
- Zero-rated, exempt, and reverse-charge tax jurisdictions.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import re
from typing import Optional, Tuple


class TaxTreatment(str, Enum):
    PERCENTAGE = 'PERCENTAGE'            # Explicit tax rate % specified (e.g. 18% GST, 20% VAT)
    FIXED_AMOUNT = 'FIXED_AMOUNT'        # Explicit dollar / currency amount quoted directly
    TAX_INCLUSIVE = 'TAX_INCLUSIVE'      # Quoted line items or totals already incorporate tax
    EXEMPT = 'EXEMPT'                    # Legally exempt from taxation
    REVERSE_CHARGE = 'REVERSE_CHARGE'    # Cross-border reverse charge / buyer self-assesses
    ZERO_RATED = 'ZERO_RATED'            # 0% tax rated export/SEZ supplies


class DiscountTreatment(str, Enum):
    PERCENTAGE = 'PERCENTAGE'            # Percentage off (e.g. 5% volume discount)
    FIXED_AMOUNT = 'FIXED_AMOUNT'        # Absolute currency deduction (e.g. $500 off total)
    NONE = 'NONE'                        # Zero discount applied


@dataclass
class NormalizedTax:
    treatment: TaxTreatment
    tax_name: str
    is_inclusive: bool
    rate_percent: Decimal
    tax_amount: Decimal
    taxable_base_amount: Decimal
    summary: str


@dataclass
class NormalizedDiscount:
    treatment: DiscountTreatment
    rate_percent: Decimal
    discount_amount: Decimal
    base_amount_before_discount: Decimal
    summary: str


def normalize_tax(
    subtotal: Decimal,
    stated_tax_amount: Optional[Decimal] = None,
    tax_rate_percent: Optional[Decimal] = None,
    tax_name_or_clause: Optional[str] = None,
    is_inclusive: bool = False,
) -> NormalizedTax:
    """
    Deterministically reconciles tax representation:
    - If tax_rate_percent is provided: calculates tax_amount = subtotal * (rate / 100).
    - If stated_tax_amount is provided: derives rate_percent = (tax_amount / subtotal) * 100.
    - If is_inclusive is True: backs out the tax amount from the gross figure:
        net_subtotal = gross / (1 + rate / 100)
        tax_amount = gross - net_subtotal
    """
    subtotal = Decimal(str(subtotal or '0.00'))
    tax_name = 'Tax / VAT'
    clause = (tax_name_or_clause or '').strip().lower()

    # 1. Detect tax jurisdiction / name
    if 'gst' in clause:
        tax_name = 'GST'
    elif 'vat' in clause:
        tax_name = 'VAT'
    elif 'sales tax' in clause:
        tax_name = 'Sales Tax'
    elif 'customs' in clause or 'duty' in clause:
        tax_name = 'Customs Duty'

    # 2. Check for Exempt / Reverse Charge / Zero-rated
    if any(k in clause for k in ('exempt', 'tax exempt', 'exemption')):
        return NormalizedTax(
            treatment=TaxTreatment.EXEMPT,
            tax_name=tax_name,
            is_inclusive=False,
            rate_percent=Decimal('0.00'),
            tax_amount=Decimal('0.00'),
            taxable_base_amount=subtotal,
            summary=f"Tax Exempt ({tax_name})",
        )

    if any(k in clause for k in ('reverse charge', 'rcm', 'reverse-charge')):
        return NormalizedTax(
            treatment=TaxTreatment.REVERSE_CHARGE,
            tax_name=f"{tax_name} (Reverse Charge)",
            is_inclusive=False,
            rate_percent=Decimal('0.00'),
            tax_amount=Decimal('0.00'),
            taxable_base_amount=subtotal,
            summary=f"Reverse Charge ({tax_name}) - Paid by Buyer",
        )

    # 3. Detect tax percentage from text if not explicitly provided
    if tax_rate_percent is None and tax_name_or_clause:
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', tax_name_or_clause)
        if pct_match:
            tax_rate_percent = Decimal(pct_match.group(1))

    # 4. Handle Tax-Inclusive pricing
    if is_inclusive or 'inclusive' in clause or 'inc. vat' in clause or 'incl. gst' in clause:
        rate = tax_rate_percent if tax_rate_percent is not None else Decimal('18.00')  # standard default if unspecified
        multiplier = Decimal('1.0') + (rate / Decimal('100.0'))
        net_base = (subtotal / multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        calc_tax = (subtotal - net_base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return NormalizedTax(
            treatment=TaxTreatment.TAX_INCLUSIVE,
            tax_name=f"{tax_name} (Inclusive)",
            is_inclusive=True,
            rate_percent=rate,
            tax_amount=calc_tax,
            taxable_base_amount=net_base,
            summary=f"{rate}% {tax_name} Inclusive (Extracted Net Base: {net_base})",
        )

    # 5. Case: Explicit Tax Rate Percentage provided (e.g. 18% GST)
    if tax_rate_percent is not None and tax_rate_percent > Decimal('0.0'):
        rate = Decimal(str(tax_rate_percent))
        calc_tax = (subtotal * (rate / Decimal('100.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return NormalizedTax(
            treatment=TaxTreatment.PERCENTAGE,
            tax_name=tax_name,
            is_inclusive=False,
            rate_percent=rate,
            tax_amount=calc_tax,
            taxable_base_amount=subtotal,
            summary=f"{rate}% {tax_name} ({calc_tax})",
        )

    # 6. Case: Explicit Fixed Tax Amount provided (e.g. $150.00 fixed tax)
    if stated_tax_amount is not None and stated_tax_amount > Decimal('0.0'):
        tax_amt = Decimal(str(stated_tax_amount))
        derived_rate = Decimal('0.00')
        if subtotal > Decimal('0.0'):
            derived_rate = ((tax_amt / subtotal) * Decimal('100.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return NormalizedTax(
            treatment=TaxTreatment.FIXED_AMOUNT,
            tax_name=tax_name,
            is_inclusive=False,
            rate_percent=derived_rate,
            tax_amount=tax_amt,
            taxable_base_amount=subtotal,
            summary=f"Fixed {tax_name} Amount ({tax_amt}, Derived Rate: {derived_rate}%)",
        )

    # Zero tax / No tax stated
    return NormalizedTax(
        treatment=TaxTreatment.ZERO_RATED,
        tax_name=tax_name,
        is_inclusive=False,
        rate_percent=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        taxable_base_amount=subtotal,
        summary='No Tax Stated (0.00)',
    )


def normalize_discount(
    gross_amount: Decimal,
    stated_discount_amount: Optional[Decimal] = None,
    discount_rate_percent: Optional[Decimal] = None,
    discount_description: Optional[str] = None,
) -> NormalizedDiscount:
    """
    Deterministically normalizes discounts:
    - Percentage discount: calculates discount_amount = gross_amount * (rate / 100).
    - Fixed discount amount: calculates derived rate = (discount_amount / gross_amount) * 100.
    """
    gross = Decimal(str(gross_amount or '0.00'))
    desc = (discount_description or '').strip()

    # 1. Detect percentage from description if rate is missing
    if discount_rate_percent is None and desc:
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', desc)
        if pct_match:
            discount_rate_percent = Decimal(pct_match.group(1))

    # 2. Percentage Discount
    if discount_rate_percent is not None and discount_rate_percent > Decimal('0.0'):
        rate = Decimal(str(discount_rate_percent))
        calc_discount = (gross * (rate / Decimal('100.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return NormalizedDiscount(
            treatment=DiscountTreatment.PERCENTAGE,
            rate_percent=rate,
            discount_amount=calc_discount,
            base_amount_before_discount=gross,
            summary=f"{rate}% Volume/Trade Discount ({calc_discount})",
        )

    # 3. Fixed Amount Discount
    if stated_discount_amount is not None and stated_discount_amount > Decimal('0.0'):
        amt = Decimal(str(stated_discount_amount))
        derived_rate = Decimal('0.00')
        if gross > Decimal('0.0'):
            derived_rate = ((amt / gross) * Decimal('100.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return NormalizedDiscount(
            treatment=DiscountTreatment.FIXED_AMOUNT,
            rate_percent=derived_rate,
            discount_amount=amt,
            base_amount_before_discount=gross,
            summary=f"Fixed Discount of {amt} (Effective Rate: {derived_rate}%)",
        )

    # Zero discount
    return NormalizedDiscount(
        treatment=DiscountTreatment.NONE,
        rate_percent=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        base_amount_before_discount=gross,
        summary='No Discount Applied',
    )
