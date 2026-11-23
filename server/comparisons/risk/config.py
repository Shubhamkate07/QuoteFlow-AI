"""
Configurable Thresholds and Policy Rules for Quotation Risk Engine.
Enables procurement organizations to customize risk sensitivities without code changes.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Set

from comparisons.risk.schemas import RiskFlagType


@dataclass
class RiskEngineConfig:
    """Configurable risk assessment parameters."""
    # Commercial & Payment Thresholds
    advance_payment_warning_threshold_pct: float = 30.0     # >= 30% advance flags WARNING
    advance_payment_critical_threshold_pct: float = 50.0    # >= 50% advance flags CRITICAL
    
    # Schedule & Delivery Tolerances
    delivery_delay_grace_days: int = 0                     # Grace days before delivery delay is flagged
    delivery_delay_critical_days: int = 14                 # Delays exceeding 14 days are CRITICAL

    # Quantity Shortfall
    quantity_shortfall_critical_threshold_pct: float = 20.0 # Shortfall > 20% is CRITICAL, else WARNING

    # Warranty
    min_acceptable_warranty_months: int = 12                # Minimum expected warranty duration

    # Mathematical Precision
    calculation_rounding_tolerance: Decimal = Decimal('0.05') # Tolerance for financial calculations

    # Pricing Variance
    price_surge_threshold_pct: float = 100.0                # Price > 100% above target/benchmark flags warning

    # Rule Filtering
    enabled_rules: Optional[Set[RiskFlagType]] = None       # If None, all 14 rules are evaluated

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'RiskEngineConfig':
        """Constructs config from a dictionary (e.g. from organization settings or request payload)."""
        if not data:
            return cls()

        enabled_rules = None
        if 'enabled_rules' in data and data['enabled_rules'] is not None:
            enabled_rules = {
                r if isinstance(r, RiskFlagType) else RiskFlagType(r)
                for r in data['enabled_rules']
            }

        return cls(
            advance_payment_warning_threshold_pct=float(data.get('advance_payment_warning_threshold_pct', 30.0)),
            advance_payment_critical_threshold_pct=float(data.get('advance_payment_critical_threshold_pct', 50.0)),
            delivery_delay_grace_days=int(data.get('delivery_delay_grace_days', 0)),
            delivery_delay_critical_days=int(data.get('delivery_delay_critical_days', 14)),
            quantity_shortfall_critical_threshold_pct=float(data.get('quantity_shortfall_critical_threshold_pct', 20.0)),
            min_acceptable_warranty_months=int(data.get('min_acceptable_warranty_months', 12)),
            calculation_rounding_tolerance=Decimal(str(data.get('calculation_rounding_tolerance', '0.05'))),
            price_surge_threshold_pct=float(data.get('price_surge_threshold_pct', 100.0)),
            enabled_rules=enabled_rules,
        )

    def is_rule_enabled(self, rule_type: RiskFlagType) -> bool:
        """Checks whether a specific risk check is active under this configuration."""
        if self.enabled_rules is None:
            return True
        return rule_type in self.enabled_rules
