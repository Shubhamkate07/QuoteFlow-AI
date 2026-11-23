"""
Deterministic mathematical formulas and arithmetic primitives for Quotation Price Comparison.
Strictly relies on Python Decimal arithmetic with ROUND_HALF_UP rounding.
Never uses floating-point types or AI approximations for financial calculations.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar

# Precision constants
CENT_PRECISION = Decimal('0.01')
UNIT_PRICE_PRECISION = Decimal('0.0001')
PERCENTAGE_PRECISION = Decimal('0.01')
QUANTITY_PRECISION = Decimal('0.0001')

T = TypeVar('T')


def to_decimal(val: Any, default: str = '0.00', precision: Optional[Decimal] = None) -> Decimal:
    """
    Safely converts any numeric input (str, int, float, Decimal) to Decimal.
    Handles None, empty strings, and whitespace gracefully.
    """
    if val is None:
        dec = Decimal(default)
    elif isinstance(val, Decimal):
        dec = val
    elif isinstance(val, (int, float)):
        dec = Decimal(str(val))
    elif isinstance(val, str):
        clean = val.strip().replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('₹', '')
        if not clean:
            dec = Decimal(default)
        else:
            try:
                dec = Decimal(clean)
            except InvalidOperation:
                dec = Decimal(default)
    else:
        try:
            dec = Decimal(str(val))
        except (InvalidOperation, TypeError, ValueError):
            dec = Decimal(default)

    if precision is not None:
        return dec.quantize(precision, rounding=ROUND_HALF_UP)
    return dec


def quantize_currency(amount: Any) -> Decimal:
    """Quantizes an amount to 2 decimal places (standard financial currency precision)."""
    return to_decimal(amount).quantize(CENT_PRECISION, rounding=ROUND_HALF_UP)


def quantize_unit_price(price: Any) -> Decimal:
    """Quantizes a unit price to 4 decimal places for micro-pricing and high precision."""
    return to_decimal(price).quantize(UNIT_PRICE_PRECISION, rounding=ROUND_HALF_UP)


def quantize_percentage(pct: Any) -> Decimal:
    """Quantizes a percentage value to 2 decimal places (e.g. 12.34%)."""
    return to_decimal(pct).quantize(PERCENTAGE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_extended_price(
    quantity: Any,
    unit_price: Any,
    discount: Any = '0.00',
    tax: Any = '0.00',
) -> Decimal:
    """
    Calculates the extended line price:
        Extended = (Quantity * Unit Price) - Line Discount + Line Tax
    Quantized to 2 decimal places.
    """
    qty = to_decimal(quantity)
    price = to_decimal(unit_price)
    disc = to_decimal(discount)
    tx = to_decimal(tax)

    raw_total = (qty * price) - disc + tx
    return quantize_currency(max(Decimal('0.00'), raw_total))


def calculate_scaled_target_price(
    target_quantity: Any,
    normalized_unit_price: Any,
) -> Decimal:
    """
    Re-scales a supplier's unit price to the RFQ target quantity:
        Scaled Extended = Target Quantity * Normalized Unit Price
    Enables apples-to-apples comparison when suppliers quote different batch quantities.
    """
    target_qty = to_decimal(target_quantity)
    unit_price = to_decimal(normalized_unit_price)
    return quantize_currency(target_qty * unit_price)


def calculate_subtotal(line_totals: Iterable[Any]) -> Decimal:
    """
    Sums line totals to compute quotation subtotal:
        Subtotal = sum(Line Extended Prices)
    """
    total = sum((to_decimal(item) for item in line_totals), Decimal('0.00'))
    return quantize_currency(total)


def calculate_grand_total(
    subtotal: Any,
    discount: Any = '0.00',
    tax: Any = '0.00',
    shipping: Any = '0.00',
) -> Decimal:
    """
    Calculates final quotation grand total:
        Grand Total = Subtotal - Order Discount + Order Tax + Shipping
    """
    sub = to_decimal(subtotal)
    disc = to_decimal(discount)
    tx = to_decimal(tax)
    ship = to_decimal(shipping)

    raw_total = sub - disc + tx + ship
    return quantize_currency(max(Decimal('0.00'), raw_total))


def calculate_price_difference(
    price: Any,
    baseline_price: Any,
) -> Decimal:
    """
    Calculates nominal price difference:
        Price Difference = Price - Baseline Price
    Positive means price is higher than baseline (premium).
    Zero means price is identical to baseline.
    Negative means price is lower than baseline (discount).
    """
    p = to_decimal(price)
    base = to_decimal(baseline_price)
    return quantize_currency(p - base)


def calculate_percentage_difference(
    price: Any,
    baseline_price: Any,
) -> Decimal:
    """
    Calculates percentage price variance against baseline:
        Percentage Difference = ((Price - Baseline Price) / Baseline Price) * 100
    If baseline <= 0 or price == baseline, returns 0.00%.
    Guarantees no ZeroDivisionError.
    """
    p = to_decimal(price)
    base = to_decimal(baseline_price)

    if base <= Decimal('0.00') or p == base:
        return Decimal('0.00')

    pct = ((p - base) / base) * Decimal('100.0')
    return quantize_percentage(pct)


def calculate_savings_amount(
    baseline_price: Any,
    best_price: Any,
) -> Decimal:
    """
    Calculates absolute savings achieved if choosing best_price instead of baseline_price:
        Savings = max(0, Baseline Price - Best Price)
    """
    base = to_decimal(baseline_price)
    best = to_decimal(best_price)
    return quantize_currency(max(Decimal('0.00'), base - best))


def calculate_savings_percentage(
    baseline_price: Any,
    best_price: Any,
) -> Decimal:
    """
    Calculates relative savings percentage:
        Savings % = (max(0, Baseline Price - Best Price) / Baseline Price) * 100
    Returns 0.00% if baseline <= 0.
    """
    base = to_decimal(baseline_price)
    best = to_decimal(best_price)

    if base <= Decimal('0.00'):
        return Decimal('0.00')

    savings = max(Decimal('0.00'), base - best)
    pct = (savings / base) * Decimal('100.0')
    return quantize_percentage(pct)


def assign_ranks(
    items: List[T],
    key_func: Callable[[T], Decimal],
    reverse: bool = False,
) -> List[Tuple[int, T]]:
    """
    Standard competition ranking (1, 2, 2, 4) with ties handled deterministically.
    Items with identical values receive the same rank.
    By default (reverse=False), lower value = lower rank number (1 is lowest / best price).
    """
    if not items:
        return []

    sorted_items = sorted(items, key=key_func, reverse=reverse)
    ranked: List[Tuple[int, T]] = []

    current_rank = 1
    for i, item in enumerate(sorted_items):
        if i > 0 and key_func(item) == key_func(sorted_items[i - 1]):
            # Tie: inherit same rank as previous item
            rank = ranked[-1][0]
        else:
            rank = i + 1
        ranked.append((rank, item))

    return ranked
