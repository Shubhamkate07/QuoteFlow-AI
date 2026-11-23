"""
Verification and Business Calculation Engine for AI-extracted quotation data.
Acts as a bridge and integration facade for the QuotationDeterministicValidator.
Ensures QuoteFlow AI NEVER blindly trusts AI outputs by performing independent arithmetic audits,
reconciliation between stated totals and line-item sums, date sanity checks, and structured flag generation.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from extractions.schemas import QuotationExtractionSchema
from extractions.validation import (
    QuotationCalculator,
    QuotationDeterministicValidator,
    ValidationFlag,
    ValidationReport,
    ValidationSeverity,
    ValidationFlagType,
)


def _to_decimal(val: Any) -> Optional[Decimal]:
    """Helper method preserving backwards-compatibility with existing code."""
    return QuotationCalculator.to_decimal(val)


@dataclass
class VerificationResult:
    """Audit report comparing AI extracted values against deterministic business arithmetic."""
    is_math_consistent: bool = True
    calculated_items_subtotal: Decimal = Decimal('0.00')
    calculated_grand_total: Decimal = Decimal('0.00')
    total_variance: Decimal = Decimal('0.00')
    validation_warnings: List[str] = field(default_factory=list)
    validation_flags: List[Dict[str, Any]] = field(default_factory=list)
    validation_report: Optional[ValidationReport] = None
    parsed_quotation_date: Optional[date] = None
    parsed_validity_date: Optional[date] = None
    normalized_currency: str = 'USD'
    items_count: int = 0


class QuotationVerificationEngine:
    """
    Independent deterministic verifier that audits Gemini's extraction output.
    Delegates validation to the QuotationDeterministicValidator and formats results.
    """

    TOLERANCE = QuotationDeterministicValidator.TOLERANCE

    @classmethod
    def verify(cls, data: QuotationExtractionSchema) -> VerificationResult:
        report = QuotationDeterministicValidator.validate(data)

        # Build list of human-readable warnings for backwards compatibility
        warning_strings = [flag.explanation for flag in report.flags]

        # Build list of structured flag dictionaries
        flag_dicts = [flag.to_dict() for flag in report.flags]

        return VerificationResult(
            is_math_consistent=report.is_math_consistent,
            calculated_items_subtotal=report.calculated_items_subtotal,
            calculated_grand_total=report.calculated_grand_total,
            total_variance=report.total_variance,
            validation_warnings=warning_strings,
            validation_flags=flag_dicts,
            validation_report=report,
            parsed_quotation_date=report.parsed_quotation_date,
            parsed_validity_date=report.parsed_validity_date,
            normalized_currency=report.normalized_currency,
            items_count=report.items_count,
        )
