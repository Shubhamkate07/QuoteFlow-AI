"""
Data schemas and serializable structures for Normalized Quotations, Line Items,
Commercial Terms, and Financial Reconciliation.
"""
from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from .currency import CurrencyConversionRecord
from .lead_time import NormalizedLeadTime
from .payment_terms import NormalizedPaymentTerms
from .warranty import NormalizedWarranty
from .tax_and_discount import NormalizedTax, NormalizedDiscount


@dataclass
class NormalizedLineItem:
    line_number: int
    description: str
    manufacturer: str
    model: str
    # Native extracted pricing
    native_quantity: Decimal
    native_unit: str
    native_unit_price: Decimal
    native_discount: Decimal
    native_tax: Decimal
    native_total: Decimal
    # Normalized UOM & converted pricing
    normalized_quantity: Decimal
    normalized_unit: str
    normalized_unit_price: Decimal
    normalized_total: Decimal
    uom_conversion_factor: Decimal
    uom_category: str
    # Specifications & matching
    specifications: List[Dict[str, Any]] = field(default_factory=list)
    rfq_item_id: Optional[str] = None
    match_type: str = 'exact'
    # Optional currency conversion citation
    currency_conversion: Optional[CurrencyConversionRecord] = None


@dataclass
class NormalizedFinancials:
    native_currency: str
    normalized_currency: str
    # Native extracted figures
    native_subtotal: Decimal
    native_tax: Decimal
    native_discount: Decimal
    native_shipping: Decimal
    native_grand_total: Decimal
    # Normalized / Converted figures
    normalized_subtotal: Decimal
    normalized_tax: Decimal
    normalized_discount: Decimal
    normalized_shipping: Decimal
    normalized_grand_total: Decimal
    # Detailed breakdowns
    tax_details: NormalizedTax
    discount_details: NormalizedDiscount
    currency_conversion: Optional[CurrencyConversionRecord] = None


@dataclass
class NormalizedCommercialTerms:
    lead_time: NormalizedLeadTime
    payment_terms: NormalizedPaymentTerms
    warranty: NormalizedWarranty
    delivery_terms: str
    notes: str = ''


@dataclass
class NormalizedQuotation:
    supplier_name: str
    quotation_number: str
    quotation_date: Optional[date]
    validity_date: Optional[date]
    financials: NormalizedFinancials
    commercial_terms: NormalizedCommercialTerms
    items: List[NormalizedLineItem]
    quotation_id: Optional[str] = None
    extraction_id: Optional[str] = None
    rfq_id: Optional[str] = None
    normalization_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts normalized data to a clean, JSON-serializable dictionary."""
        def _serialize(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            if is_dataclass(obj) and not isinstance(obj, type):
                return {k: _serialize(getattr(obj, k)) for k in obj.__dataclass_fields__}
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [_serialize(item) for item in obj]
            return obj

        return _serialize(self)
