"""
Schemas and Data Structures for Quotation Risk Flag Engine.
Defines strongly typed models for commercial, technical, and operational risk assessment.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskSeverity(str, Enum):
    """Impact severity of an identified procurement risk."""
    CRITICAL = 'critical'    # Blocker: non-compliant spec, expired terms, severe financial exposure
    WARNING = 'warning'      # Moderate risk: delivery delay, missing warranty, minor math error
    INFO = 'info'            # Informational note or mild variance requiring buyer awareness


class RiskFlagType(str, Enum):
    """Specific categories of quotation risk flags."""
    SPECIFICATION_MISMATCH = 'specification_mismatch'
    MISSING_SPECIFICATIONS = 'missing_specifications'
    QUANTITY_SHORTFALL = 'quantity_shortfall'
    DELIVERY_DELAY = 'delivery_delay'
    EXPIRED_QUOTATION = 'expired_quotation'
    MISSING_QUOTATION_VALIDITY = 'missing_quotation_validity'
    PAYMENT_RISK = 'payment_risk'
    HIGH_ADVANCE_PAYMENT = 'high_advance_payment'
    NO_WARRANTY = 'no_warranty'
    MISSING_WARRANTY = 'missing_warranty'
    CALCULATION_ERROR = 'calculation_error'
    PRICE_INCONSISTENCY = 'price_inconsistency'
    MISSING_QUOTATION_INFORMATION = 'missing_quotation_information'
    CURRENCY_MISMATCH = 'currency_mismatch'


@dataclass
class RiskFlag:
    """Individual quotation risk flag with authoritative evidence and actionable recommendation."""
    type: RiskFlagType
    severity: RiskSeverity
    title: str
    description: str
    affected_field_or_item: str
    evidence: str
    recommended_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value if isinstance(self.type, Enum) else str(self.type),
            'severity': self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            'title': self.title,
            'description': self.description,
            'affected_field_or_item': self.affected_field_or_item,
            'evidence': self.evidence,
            'recommended_action': self.recommended_action,
            'metadata': self.metadata,
        }


@dataclass
class QuotationRiskReport:
    """Comprehensive risk assessment report for an individual quotation."""
    quotation_id: Optional[str]
    quotation_number: str
    supplier_name: str
    rfq_id: Optional[str]
    evaluation_date: date
    overall_risk_score: float                # 0.0 (safest) to 100.0 (highest risk)
    overall_risk_level: str                  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    flags: List[RiskFlag] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    is_acceptable: bool = True               # True if no CRITICAL risk flags exist

    def to_dict(self) -> Dict[str, Any]:
        return {
            'quotation_id': self.quotation_id,
            'quotation_number': self.quotation_number,
            'supplier_name': self.supplier_name,
            'rfq_id': self.rfq_id,
            'evaluation_date': self.evaluation_date.isoformat() if isinstance(self.evaluation_date, date) else str(self.evaluation_date),
            'overall_risk_score': round(self.overall_risk_score, 2),
            'overall_risk_level': self.overall_risk_level,
            'flags': [flag.to_dict() for flag in self.flags],
            'critical_count': self.critical_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'is_acceptable': self.is_acceptable,
        }
