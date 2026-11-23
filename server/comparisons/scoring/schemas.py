"""
Schemas and Data Structures for Explainable Supplier Scoring Engine in QuoteFlow AI.
Provides strongly typed dataclasses for factor-by-factor auditing, calculation formulas,
and overall RFQ vendor rankings.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ScoringFactor(str, Enum):
    """The 5 primary evaluation dimensions for supplier quotation scoring."""
    PRICE = 'price'
    SPEC_MATCH = 'spec_match'
    DELIVERY = 'delivery'
    PAYMENT_TERMS = 'payment_terms'
    WARRANTY = 'warranty'


@dataclass
class FactorScoreBreakdown:
    """
    Detailed, audited calculation record for a single scoring factor.
    Guarantees that no scoring math is hidden from the procurement reviewer.
    """
    factor: ScoringFactor
    name: str                           # Display title, e.g. "Price Competitiveness"
    raw_value: str                      # Stated value, e.g. "$1,200.00", "Net 30", "24 months"
    raw_metric: Optional[float]         # Quantitative representation, e.g. 1200.0, 30.0, 24.0
    normalized_score: float             # 0.0 to 100.0 rating for this factor
    weight_pct: float                   # Weight percentage applied, e.g. 40.0%
    weighted_score: float               # normalized_score * (weight_pct / 100.0)
    formula_applied: str                # Exact mathematical formula string, e.g. "(1000 / 1200) * 100 = 83.33"
    explanation: str                    # Human-readable justification of the score

    def to_dict(self) -> Dict[str, Any]:
        return {
            'factor': self.factor.value if isinstance(self.factor, Enum) else str(self.factor),
            'name': self.name,
            'raw_value': self.raw_value,
            'raw_metric': self.raw_metric,
            'normalized_score': round(self.normalized_score, 2),
            'weight_pct': round(self.weight_pct, 2),
            'weighted_score': round(self.weighted_score, 2),
            'formula_applied': self.formula_applied,
            'explanation': self.explanation,
        }


@dataclass
class SupplierScoreReport:
    """
    Complete explainable score evaluation for an individual supplier quotation.
    """
    supplier_id: Optional[str]
    supplier_name: str
    quotation_id: Optional[str]
    quotation_number: str
    final_score: float                                      # 0.0 to 100.0 (sum of all weighted factor scores)
    rank: int = 1                                           # Comparative standing among quotes (1 = Best)
    factors: Dict[str, FactorScoreBreakdown] = field(default_factory=dict)
    is_recommended_for_consideration: bool = True           # False if critical non-compliance or final score < 30
    advisory_notes: List[str] = field(default_factory=list) # Critical takeaways for procurement buyers

    def to_dict(self) -> Dict[str, Any]:
        return {
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'quotation_id': self.quotation_id,
            'quotation_number': self.quotation_number,
            'final_score': round(self.final_score, 2),
            'rank': self.rank,
            'factors': {k: v.to_dict() for k, v in self.factors.items()},
            'is_recommended_for_consideration': self.is_recommended_for_consideration,
            'advisory_notes': self.advisory_notes,
        }


@dataclass
class RFQSupplierScoringSummary:
    """
    Comprehensive multi-supplier comparison summary across an entire RFQ.
    Includes explicit methodology, benchmarks, rankings, and documented system limitations.
    """
    rfq_id: Optional[str]
    rfq_number: str
    rfq_title: str
    weights_applied: Dict[str, float]
    benchmarks: Dict[str, Any]
    rankings: List[SupplierScoreReport] = field(default_factory=list)
    scoring_limitations: List[str] = field(default_factory=list)
    disclaimer: str = (
        "This scoring engine is an explainable decision-support tool. "
        "It does NOT automatically select or purchase from any supplier. "
        "Final contract awards require professional procurement review and approval."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rfq_id': self.rfq_id,
            'rfq_number': self.rfq_number,
            'rfq_title': self.rfq_title,
            'weights_applied': {k: round(v, 2) for k, v in self.weights_applied.items()},
            'benchmarks': self.benchmarks,
            'rankings': [r.to_dict() for r in self.rankings],
            'scoring_limitations': self.scoring_limitations,
            'disclaimer': self.disclaimer,
        }
