"""
Configurable Scoring Weights and Mathematical Validation.
Guarantees that user-defined evaluation weights are non-negative and strictly total 100%.
"""
from dataclasses import dataclass
from typing import Any, Dict, Union

from comparisons.scoring.schemas import ScoringFactor


class WeightValidationError(ValueError):
    """Raised when scoring weights violate business validation constraints."""
    pass


@dataclass
class ScoringWeights:
    """
    Configurable scoring weights for supplier evaluation.
    Default distribution:
    - Price: 40%
    - Specification match: 30%
    - Delivery: 15%
    - Payment terms: 10%
    - Warranty: 5%
    Total: 100%
    """
    price: float = 40.0
    spec_match: float = 30.0
    delivery: float = 15.0
    payment_terms: float = 10.0
    warranty: float = 5.0

    def to_dict(self) -> Dict[str, float]:
        return {
            ScoringFactor.PRICE.value: self.price,
            ScoringFactor.SPEC_MATCH.value: self.spec_match,
            ScoringFactor.DELIVERY.value: self.delivery,
            ScoringFactor.PAYMENT_TERMS.value: self.payment_terms,
            ScoringFactor.WARRANTY.value: self.warranty,
        }

    def get_weight(self, factor: Union[ScoringFactor, str]) -> float:
        """Retrieves weight percentage for a given factor."""
        key = factor.value if isinstance(factor, ScoringFactor) else str(factor).lower()
        mapping = {
            'price': self.price,
            'spec_match': self.spec_match,
            'specification_match': self.spec_match,
            'delivery': self.delivery,
            'payment_terms': self.payment_terms,
            'payment': self.payment_terms,
            'warranty': self.warranty,
        }
        if key not in mapping:
            raise WeightValidationError(f"Unknown scoring factor: '{factor}'.")
        return mapping[key]


DEFAULT_SCORING_WEIGHTS = ScoringWeights()


def validate_weights(weights_input: Union[ScoringWeights, Dict[str, Any], None]) -> ScoringWeights:
    """
    Strictly validates scoring weights:
    1. Checks for non-negative values for all factors.
    2. Supports both percentage scale (sum = 100.0) and decimal fraction scale (sum = 1.0).
    3. Guarantees the weights sum to 100.0% within a tolerance of 0.01%.
    4. Raises WeightValidationError with explicit diagnostics if validation fails.
    """
    if weights_input is None:
        return ScoringWeights()

    if isinstance(weights_input, ScoringWeights):
        raw_dict = weights_input.to_dict()
    elif isinstance(weights_input, dict):
        raw_dict = weights_input.copy()
    else:
        raise WeightValidationError(f"Weights must be a dictionary or ScoringWeights instance, got {type(weights_input)}.")

    # Canonicalize factor keys
    standardized: Dict[str, float] = {}
    key_aliases = {
        'price': 'price',
        'spec_match': 'spec_match',
        'specification_match': 'spec_match',
        'specifications': 'spec_match',
        'specs': 'spec_match',
        'delivery': 'delivery',
        'schedule': 'delivery',
        'lead_time': 'delivery',
        'payment_terms': 'payment_terms',
        'payment': 'payment_terms',
        'commercial_terms': 'payment_terms',
        'warranty': 'warranty',
    }

    for k, v in raw_dict.items():
        clean_k = str(k).strip().lower()
        if clean_k in key_aliases:
            canon = key_aliases[clean_k]
            try:
                val = float(v)
            except (ValueError, TypeError):
                raise WeightValidationError(f"Weight for '{k}' must be a numeric value, got '{v}'.")
            standardized[canon] = val
        else:
            raise WeightValidationError(
                f"Unknown scoring factor '{k}'. Allowed factors: price, spec_match, delivery, payment_terms, warranty."
            )

    # Ensure all 5 factors are specified
    required_factors = ['price', 'spec_match', 'delivery', 'payment_terms', 'warranty']
    missing_factors = [f for f in required_factors if f not in standardized]
    if missing_factors:
        raise WeightValidationError(f"Missing required scoring factors: {', '.join(missing_factors)}.")

    # Validate non-negativity
    negative_factors = [f"{f} ({val})" for f, val in standardized.items() if val < 0.0]
    if negative_factors:
        raise WeightValidationError(f"Weights cannot be negative: {', '.join(negative_factors)}.")

    # Check sum
    total_sum = sum(standardized[f] for f in required_factors)

    # Check if user provided decimal fractions summing to ~1.0 (e.g. 0.40, 0.30, 0.15, 0.10, 0.05)
    if 0.99 <= total_sum <= 1.01:
        # Scale to 100%
        standardized = {f: standardized[f] * 100.0 for f in required_factors}
        total_sum = sum(standardized[f] for f in required_factors)

    # Check that sum is exactly 100.0% within floating point tolerance
    if abs(total_sum - 100.0) > 0.01:
        raise WeightValidationError(
            f"Weights must total exactly 100%. Current sum: {total_sum:.2f}% "
            f"(price: {standardized['price']:.1f}%, spec_match: {standardized['spec_match']:.1f}%, "
            f"delivery: {standardized['delivery']:.1f}%, payment_terms: {standardized['payment_terms']:.1f}%, "
            f"warranty: {standardized['warranty']:.1f}%)."
        )

    return ScoringWeights(
        price=standardized['price'],
        spec_match=standardized['spec_match'],
        delivery=standardized['delivery'],
        payment_terms=standardized['payment_terms'],
        warranty=standardized['warranty'],
    )
