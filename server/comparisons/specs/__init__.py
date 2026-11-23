"""
Specification Matching Engine Package for QuoteFlow AI.
"""
from comparisons.specs.schemas import (
    DiscrepancySeverity,
    ItemSpecMatchSummary,
    SingleSpecMatchResult,
    SpecImportance,
    SpecMatchStatus,
    SpecVerdict,
)
from comparisons.specs.canonical import (
    canonicalize_key,
    normalize_voltage,
    parse_distance_dimension,
    parse_ip_rating,
    extract_connection_tokens,
)
from comparisons.specs.rules import DeterministicSpecMatcher
from comparisons.specs.ai_matcher import AISpecMatcher
from comparisons.specs.engine import SpecificationMatchingEngine

__all__ = [
    'DiscrepancySeverity',
    'ItemSpecMatchSummary',
    'SingleSpecMatchResult',
    'SpecImportance',
    'SpecMatchStatus',
    'SpecVerdict',
    'canonicalize_key',
    'normalize_voltage',
    'parse_distance_dimension',
    'parse_ip_rating',
    'extract_connection_tokens',
    'DeterministicSpecMatcher',
    'AISpecMatcher',
    'SpecificationMatchingEngine',
]
