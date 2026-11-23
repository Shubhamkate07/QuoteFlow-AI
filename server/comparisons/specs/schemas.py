"""
Schemas and Data Structures for Technical Specification Matching.
Defines strongly typed models for comparing RFQ technical requirements against
supplier quotation specifications.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SpecMatchStatus(str, Enum):
    """Lifecycle classification for an individual technical specification comparison."""
    EXACT_MATCH = 'exact_match'        # Exact or normalized technical equivalence (e.g. 24V DC vs 24V DC)
    MISMATCH = 'mismatch'              # Conflicting or incompatible technical value (e.g. PNP vs NPN)
    MISSING = 'missing'                # Required RFQ specification not provided by the supplier
    UNCLEAR = 'unclear'                # Ambiguous, generic, or conditional specification requiring clarification
    ADDITIONAL = 'additional'          # Extra specification offered by supplier not requested in the RFQ


class DiscrepancySeverity(str, Enum):
    """Impact severity of a specification discrepancy on technical feasibility."""
    CRITICAL = 'critical'              # Blocker: completely incompatible (e.g. NPN vs PNP, 230V AC vs 24V DC)
    WARNING = 'warning'                # Technical variance that may be workable with engineering approval
    INFO = 'info'                      # Minor phrasing difference or additional capability
    NONE = 'none'                      # No discrepancy (exact match)


class SpecImportance(str, Enum):
    """Criticality of the specification for the procurement requirement."""
    MANDATORY = 'mandatory'            # Non-negotiable requirement
    PREFERRED = 'preferred'            # Preferred specification
    NICE_TO_HAVE = 'nice_to_have'      # Optional enhancement


class SpecVerdict(str, Enum):
    """Overall compliance verdict for an item or quotation."""
    COMPLIANT = 'compliant'            # All mandatory specifications match
    SPEC_VARIANCE = 'spec_variance'    # Minor non-critical variances present
    NON_COMPLIANT = 'non_compliant'    # One or more critical/mandatory mismatches
    INCOMPLETE = 'incomplete'          # Mandatory specifications missing from quotation


@dataclass
class SingleSpecMatchResult:
    """Detailed matching result for a single specification parameter."""
    parameter_name: str                               # e.g. "Output", "Voltage", "Sensing distance"
    canonical_key: str                                # e.g. "output", "voltage", "sensing_distance"
    requirement_value: Optional[str]                  # Value requested by RFQ (e.g. "PNP", "24V DC", "8mm")
    requirement_unit: Optional[str] = None            # Optional unit (e.g. "mm", "V DC")
    supplier_value: Optional[str] = None              # Value quoted by supplier (e.g. "NPN", "24V DC", "8mm")
    status: SpecMatchStatus = SpecMatchStatus.UNCLEAR # Match classification
    explanation: str = ''                             # Authoritative technical explanation of the match/mismatch
    evidence: Optional[str] = None                    # Document citation or source text snippet
    confidence: float = 1.0                           # 0.0 to 1.0 (1.0 for deterministic rules)
    is_deterministic: bool = True                     # True if decided by deterministic rules, False if via AI
    importance: SpecImportance = SpecImportance.MANDATORY
    severity: DiscrepancySeverity = DiscrepancySeverity.NONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            'parameter_name': self.parameter_name,
            'canonical_key': self.canonical_key,
            'requirement_value': self.requirement_value,
            'requirement_unit': self.requirement_unit,
            'supplier_value': self.supplier_value,
            'status': self.status.value if isinstance(self.status, Enum) else self.status,
            'explanation': self.explanation,
            'evidence': self.evidence,
            'confidence': round(self.confidence, 4),
            'is_deterministic': self.is_deterministic,
            'importance': self.importance.value if isinstance(self.importance, Enum) else self.importance,
            'severity': self.severity.value if isinstance(self.severity, Enum) else self.severity,
        }


@dataclass
class ItemSpecMatchSummary:
    """Aggregate specification compliance evaluation for an RFQ line item vs a supplier's quote."""
    item_name: str
    rfq_item_id: Optional[str] = None
    quotation_item_id: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None

    # Quantitative compliance metrics
    spec_match_score: float = 0.0                     # 0.0 to 100.0% compliance score
    total_requirements_count: int = 0
    exact_matches_count: int = 0
    mismatches_count: int = 0
    missing_count: int = 0
    unclear_count: int = 0
    additional_count: int = 0

    has_critical_mismatches: bool = False
    verdict: SpecVerdict = SpecVerdict.COMPLIANT

    # Individual parameter comparison records
    matches: List[SingleSpecMatchResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_name': self.item_name,
            'rfq_item_id': self.rfq_item_id,
            'quotation_item_id': self.quotation_item_id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'spec_match_score': round(self.spec_match_score, 2),
            'total_requirements_count': self.total_requirements_count,
            'exact_matches_count': self.exact_matches_count,
            'mismatches_count': self.mismatches_count,
            'missing_count': self.missing_count,
            'unclear_count': self.unclear_count,
            'additional_count': self.additional_count,
            'has_critical_mismatches': self.has_critical_mismatches,
            'verdict': self.verdict.value if isinstance(self.verdict, Enum) else self.verdict,
            'matches': [m.to_dict() for m in self.matches],
        }
