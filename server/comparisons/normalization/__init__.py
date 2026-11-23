"""
QuoteFlow AI Data Normalization Engine.
Public interface for deterministic quotation data normalization.
"""
from .uom import (
    UOMCategory,
    UOMDefinition,
    canonicalize_uom,
    can_convert_uom,
    get_uom_conversion_factor,
    convert_quantity_and_price,
)
from .currency import (
    CurrencyMetadata,
    ExchangeRate,
    ExchangeRateTable,
    CurrencyConversionRecord,
    CurrencyConversionService,
    MissingExchangeRateError,
    InvalidCurrencyCodeError,
    normalize_currency_code,
    get_currency_decimals,
)
from .lead_time import (
    NormalizedLeadTime,
    normalize_lead_time,
)
from .payment_terms import (
    PaymentTermCategory,
    PaymentMilestone,
    NormalizedPaymentTerms,
    normalize_payment_terms,
)
from .warranty import (
    WarrantyType,
    NormalizedWarranty,
    normalize_warranty,
)
from .tax_and_discount import (
    TaxTreatment,
    DiscountTreatment,
    NormalizedTax,
    NormalizedDiscount,
    normalize_tax,
    normalize_discount,
)
from .schemas import (
    NormalizedLineItem,
    NormalizedFinancials,
    NormalizedCommercialTerms,
    NormalizedQuotation,
)
from .service import QuotationNormalizationService

__all__ = [
    # UOM
    'UOMCategory',
    'UOMDefinition',
    'canonicalize_uom',
    'can_convert_uom',
    'get_uom_conversion_factor',
    'convert_quantity_and_price',
    # Currency
    'CurrencyMetadata',
    'ExchangeRate',
    'ExchangeRateTable',
    'CurrencyConversionRecord',
    'CurrencyConversionService',
    'MissingExchangeRateError',
    'InvalidCurrencyCodeError',
    'normalize_currency_code',
    'get_currency_decimals',
    # Commercial
    'NormalizedLeadTime',
    'normalize_lead_time',
    'PaymentTermCategory',
    'PaymentMilestone',
    'NormalizedPaymentTerms',
    'normalize_payment_terms',
    'WarrantyType',
    'NormalizedWarranty',
    'normalize_warranty',
    # Tax & Discount
    'TaxTreatment',
    'DiscountTreatment',
    'NormalizedTax',
    'NormalizedDiscount',
    'normalize_tax',
    'normalize_discount',
    # Master Schemas & Service
    'NormalizedLineItem',
    'NormalizedFinancials',
    'NormalizedCommercialTerms',
    'NormalizedQuotation',
    'QuotationNormalizationService',
]
