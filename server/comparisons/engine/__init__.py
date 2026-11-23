"""
Deterministic Price Comparison Engine package for QuoteFlow AI.
"""
from .comparator import PriceComparisonEngine
from .formulas import (
    CENT_PRECISION,
    PERCENTAGE_PRECISION,
    UNIT_PRICE_PRECISION,
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
    InconsistencySeverity,
    ItemCompatibilityStatus,
    LineItemComparisonResult,
    QuotationComparisonResult,
    RFQComparisonSummary,
    SupplierItemBid,
)
from .validator import (
    ComparisonValidationError,
    ComparisonValidator,
)

__all__ = [
    'PriceComparisonEngine',
    'ComparisonValidator',
    'ComparisonValidationError',
    'CalculationInconsistency',
    'InconsistencySeverity',
    'ItemCompatibilityStatus',
    'SupplierItemBid',
    'LineItemComparisonResult',
    'QuotationComparisonResult',
    'RFQComparisonSummary',
    'to_decimal',
    'quantize_currency',
    'quantize_unit_price',
    'quantize_percentage',
    'calculate_extended_price',
    'calculate_scaled_target_price',
    'calculate_subtotal',
    'calculate_grand_total',
    'calculate_price_difference',
    'calculate_percentage_difference',
    'calculate_savings_amount',
    'calculate_savings_percentage',
    'assign_ranks',
    'CENT_PRECISION',
    'UNIT_PRICE_PRECISION',
    'PERCENTAGE_PRECISION',
]
