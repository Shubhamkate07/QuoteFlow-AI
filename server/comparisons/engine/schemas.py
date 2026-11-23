"""
Schemas and serializable data structures for Deterministic Quotation Comparison.
Provides strongly typed dataclasses for line item matrices, quotation reconciliation,
and overall RFQ procurement summaries.
"""
from dataclasses import dataclass, field, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ItemCompatibilityStatus(str, Enum):
    """Compatibility lifecycle status for an item bid relative to an RFQ line item."""
    COMPATIBLE = 'compatible'          # Exact or standardized match, comparable
    SPEC_VARIANCE = 'spec_variance'    # Alternate spec/material; comparable with variance flag
    INCOMPATIBLE = 'incompatible'      # Unit/domain mismatch or cannot be compared; excluded from best price
    UNMATCHED = 'unmatched'            # Extra item quoted by supplier, not in RFQ
    UNQUOTED = 'unquoted'              # Required RFQ item omitted by supplier


class InconsistencySeverity(str, Enum):
    """Severity of mathematical or document inconsistency."""
    ERROR = 'error'        # Arithmetic mismatch exceeding rounding tolerance
    WARNING = 'warning'    # Missing term or potential variance
    INFO = 'info'          # Informational note (e.g. shipping excluded by Incoterm)


@dataclass
class CalculationInconsistency:
    """Detailed record of a mathematical or financial inconsistency in a quotation."""
    scope: str                         # 'line_item', 'subtotal', 'tax', 'discount', 'shipping', 'grand_total'
    field_name: str                    # e.g. 'subtotal', 'items[0].line_total'
    stated_value: Decimal              # Value printed / stated on document
    calculated_value: Decimal          # Value determined by verified arithmetic
    variance: Decimal                  # stated_value - calculated_value
    severity: InconsistencySeverity
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scope': self.scope,
            'field_name': self.field_name,
            'stated_value': float(self.stated_value),
            'calculated_value': float(self.calculated_value),
            'variance': float(self.variance),
            'severity': self.severity.value if isinstance(self.severity, Enum) else self.severity,
            'explanation': self.explanation,
        }


@dataclass
class SupplierItemBid:
    """Individual supplier bid on an RFQ line item, normalized to comparison currency and RFQ UOM."""
    quotation_id: str
    supplier_id: str
    supplier_name: str
    quote_number: str

    # Quoted native details
    quoted_quantity: Decimal
    quoted_unit: str
    quoted_unit_price: Decimal
    quoted_line_total: Decimal

    # Normalized details (in comparison currency and RFQ UOM)
    normalized_quantity: Decimal
    normalized_unit: str
    normalized_unit_price: Decimal
    normalized_line_discount: Decimal
    normalized_line_tax: Decimal

    # Extended price calculations
    extended_price_quoted_qty: Decimal   # qty_quoted * unit_price - disc + tax
    extended_price_target_qty: Decimal   # target_rfq_qty * normalized_unit_price

    # Compatibility & Variance
    compatibility_status: ItemCompatibilityStatus
    incompatibility_reason: str = ''
    material_spec_quoted: str = ''
    has_spec_variance: bool = False
    spec_variance_notes: str = ''

    # Comparative metrics against lowest bidder (computed across all bids for this item)
    price_difference: Decimal = Decimal('0.00')
    percentage_difference: Decimal = Decimal('0.00')
    is_lowest_unit_price: bool = False
    is_lowest_extended_price: bool = False
    item_rank: int = 1

    # Inconsistency flags
    has_calculation_inconsistency: bool = False
    inconsistencies: List[CalculationInconsistency] = field(default_factory=list)

    # Detailed specification match summary (optional)
    spec_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'quotation_id': self.quotation_id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'quote_number': self.quote_number,
            'quoted_quantity': float(self.quoted_quantity),
            'quoted_unit': self.quoted_unit,
            'quoted_unit_price': float(self.quoted_unit_price),
            'quoted_line_total': float(self.quoted_line_total),
            'normalized_quantity': float(self.normalized_quantity),
            'normalized_unit': self.normalized_unit,
            'normalized_unit_price': float(self.normalized_unit_price),
            'normalized_line_discount': float(self.normalized_line_discount),
            'normalized_line_tax': float(self.normalized_line_tax),
            'extended_price_quoted_qty': float(self.extended_price_quoted_qty),
            'extended_price_target_qty': float(self.extended_price_target_qty),
            'compatibility_status': self.compatibility_status.value if isinstance(self.compatibility_status, Enum) else self.compatibility_status,
            'incompatibility_reason': self.incompatibility_reason,
            'material_spec_quoted': self.material_spec_quoted,
            'has_spec_variance': self.has_spec_variance,
            'spec_variance_notes': self.spec_variance_notes,
            'price_difference': float(self.price_difference),
            'percentage_difference': float(self.percentage_difference),
            'is_lowest_unit_price': self.is_lowest_unit_price,
            'is_lowest_extended_price': self.is_lowest_extended_price,
            'item_rank': self.item_rank,
            'has_calculation_inconsistency': self.has_calculation_inconsistency,
            'inconsistencies': [inc.to_dict() for inc in self.inconsistencies],
            'spec_summary': self.spec_summary,
        }


@dataclass
class LineItemComparisonResult:
    """Comprehensive side-by-side comparison for a single RFQ line item."""
    rfq_item_id: str
    position: int
    item_name: str
    description: str
    target_quantity: Decimal
    target_unit: str
    target_unit_price: Optional[Decimal] = None   # Target/Budget price if specified on RFQ

    # Supplier bids keyed by supplier_id
    bids: Dict[str, SupplierItemBid] = field(default_factory=dict)

    # Lowest comparable metrics
    lowest_unit_price: Optional[Decimal] = None
    lowest_extended_price: Optional[Decimal] = None
    lowest_bidder_id: Optional[str] = None
    lowest_bidder_name: Optional[str] = None

    # Benchmark metrics
    highest_extended_price: Optional[Decimal] = None
    average_extended_price: Optional[Decimal] = None
    spread_amount: Decimal = Decimal('0.00')           # highest - lowest
    spread_percentage: Decimal = Decimal('0.00')       # ((highest - lowest) / lowest) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rfq_item_id': self.rfq_item_id,
            'position': self.position,
            'item_name': self.item_name,
            'description': self.description,
            'target_quantity': float(self.target_quantity),
            'target_unit': self.target_unit,
            'target_unit_price': float(self.target_unit_price) if self.target_unit_price is not None else None,
            'bids': {k: v.to_dict() for k, v in self.bids.items()},
            'lowest_unit_price': float(self.lowest_unit_price) if self.lowest_unit_price is not None else None,
            'lowest_extended_price': float(self.lowest_extended_price) if self.lowest_extended_price is not None else None,
            'lowest_bidder_id': self.lowest_bidder_id,
            'lowest_bidder_name': self.lowest_bidder_name,
            'highest_extended_price': float(self.highest_extended_price) if self.highest_extended_price is not None else None,
            'average_extended_price': float(self.average_extended_price) if self.average_extended_price is not None else None,
            'spread_amount': float(self.spread_amount),
            'spread_percentage': float(self.spread_percentage),
        }


@dataclass
class QuotationComparisonResult:
    """Quotation-level comparison row including reconciled financial totals and commercial terms."""
    quotation_id: str
    quotation_number: str
    supplier_id: str
    supplier_name: str
    quote_date: Optional[date]
    valid_until: Optional[date]

    # Currencies
    native_currency: str
    comparison_currency: str
    exchange_rate_applied: Optional[Decimal] = None
    rate_source: str = ''
    rate_date: Optional[date] = None

    # Scope & Coverage
    total_rfq_items: int = 0
    covered_items_count: int = 0
    coverage_percentage: Decimal = Decimal('100.00')
    is_full_coverage: bool = True
    unquoted_item_ids: List[str] = field(default_factory=list)

    # Reconciled Financials (in comparison_currency)
    subtotal: Decimal = Decimal('0.00')
    discounts: Decimal = Decimal('0.00')
    taxes: Decimal = Decimal('0.00')
    shipping: Decimal = Decimal('0.00')
    grand_total: Decimal = Decimal('0.00')

    # Target Scaled Grand Total (sum of items scaled to RFQ target quantities + order level taxes/shipping)
    target_scaled_grand_total: Decimal = Decimal('0.00')

    # Document Stated Totals & Inconsistency Audit
    stated_subtotal: Optional[Decimal] = None
    stated_grand_total: Optional[Decimal] = None
    has_calculation_inconsistencies: bool = False
    inconsistencies: List[CalculationInconsistency] = field(default_factory=list)

    # Comparability
    is_comparable: bool = True
    incomparability_reasons: List[str] = field(default_factory=list)

    # Rank and Relative Variances
    rank: int = 1
    is_lowest_grand_total: bool = False
    price_difference_vs_lowest: Decimal = Decimal('0.00')
    percentage_difference_vs_lowest: Decimal = Decimal('0.00')
    potential_savings_vs_this_quote: Decimal = Decimal('0.00')

    # Commercial Terms
    delivery_lead_weeks: int = 0
    delivery_lead_days: int = 0
    payment_terms: str = ''
    warranty_months: int = 0
    warranty_terms: str = ''
    incoterms: str = ''
    notes: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'quotation_id': self.quotation_id,
            'quotation_number': self.quotation_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'quote_date': self.quote_date.isoformat() if self.quote_date else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'native_currency': self.native_currency,
            'comparison_currency': self.comparison_currency,
            'exchange_rate_applied': float(self.exchange_rate_applied) if self.exchange_rate_applied is not None else None,
            'rate_source': self.rate_source,
            'rate_date': self.rate_date.isoformat() if self.rate_date else None,
            'total_rfq_items': self.total_rfq_items,
            'covered_items_count': self.covered_items_count,
            'coverage_percentage': float(self.coverage_percentage),
            'is_full_coverage': self.is_full_coverage,
            'unquoted_item_ids': self.unquoted_item_ids,
            'subtotal': float(self.subtotal),
            'discounts': float(self.discounts),
            'taxes': float(self.taxes),
            'shipping': float(self.shipping),
            'grand_total': float(self.grand_total),
            'target_scaled_grand_total': float(self.target_scaled_grand_total),
            'stated_subtotal': float(self.stated_subtotal) if self.stated_subtotal is not None else None,
            'stated_grand_total': float(self.stated_grand_total) if self.stated_grand_total is not None else None,
            'has_calculation_inconsistencies': self.has_calculation_inconsistencies,
            'inconsistencies': [inc.to_dict() for inc in self.inconsistencies],
            'is_comparable': self.is_comparable,
            'incomparability_reasons': self.incomparability_reasons,
            'rank': self.rank,
            'is_lowest_grand_total': self.is_lowest_grand_total,
            'price_difference_vs_lowest': float(self.price_difference_vs_lowest),
            'percentage_difference_vs_lowest': float(self.percentage_difference_vs_lowest),
            'potential_savings_vs_this_quote': float(self.potential_savings_vs_this_quote),
            'delivery_lead_weeks': self.delivery_lead_weeks,
            'delivery_lead_days': self.delivery_lead_days,
            'payment_terms': self.payment_terms,
            'warranty_months': self.warranty_months,
            'warranty_terms': self.warranty_terms,
            'incoterms': self.incoterms,
            'notes': self.notes,
        }


@dataclass
class RFQComparisonSummary:
    """Complete multi-vendor comparison output across an entire RFQ."""
    rfq_id: str
    rfq_number: str
    rfq_title: str
    comparison_currency: str
    quotations_compared_count: int

    # Overall Winner & Benchmark Totals
    lowest_grand_total: Optional[Decimal] = None
    lowest_quote_id: Optional[str] = None
    lowest_supplier_name: Optional[str] = None
    highest_grand_total: Optional[Decimal] = None
    highest_supplier_name: Optional[str] = None
    average_grand_total: Optional[Decimal] = None
    median_grand_total: Optional[Decimal] = None

    # Potential Single-Award Savings
    max_savings_amount: Decimal = Decimal('0.00')
    max_savings_percentage: Decimal = Decimal('0.00')

    # Split-Award / Cherry-Pick Potential
    cherry_pick_total: Decimal = Decimal('0.00')
    cherry_pick_savings: Decimal = Decimal('0.00')
    cherry_pick_savings_percentage: Decimal = Decimal('0.00')

    # Detailed Matrices
    items_matrix: List[LineItemComparisonResult] = field(default_factory=list)
    quotations: List[QuotationComparisonResult] = field(default_factory=list)

    # General Audit & Warnings
    warnings: List[str] = field(default_factory=list)
    calculation_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rfq_id': self.rfq_id,
            'rfq_number': self.rfq_number,
            'rfq_title': self.rfq_title,
            'comparison_currency': self.comparison_currency,
            'quotations_compared_count': self.quotations_compared_count,
            'lowest_grand_total': float(self.lowest_grand_total) if self.lowest_grand_total is not None else None,
            'lowest_quote_id': self.lowest_quote_id,
            'lowest_supplier_name': self.lowest_supplier_name,
            'highest_grand_total': float(self.highest_grand_total) if self.highest_grand_total is not None else None,
            'highest_supplier_name': self.highest_supplier_name,
            'average_grand_total': float(self.average_grand_total) if self.average_grand_total is not None else None,
            'median_grand_total': float(self.median_grand_total) if self.median_grand_total is not None else None,
            'max_savings_amount': float(self.max_savings_amount),
            'max_savings_percentage': float(self.max_savings_percentage),
            'cherry_pick_total': float(self.cherry_pick_total),
            'cherry_pick_savings': float(self.cherry_pick_savings),
            'cherry_pick_savings_percentage': float(self.cherry_pick_savings_percentage),
            'items_matrix': [item.to_dict() for item in self.items_matrix],
            'quotations': [q.to_dict() for q in self.quotations],
            'warnings': self.warnings,
            'calculation_timestamp': self.calculation_timestamp.isoformat(),
        }
