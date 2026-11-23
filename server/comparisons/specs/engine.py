"""
Specification Matching Engine for QuoteFlow AI.
Performs comprehensive comparison between RFQ engineering requirements and supplier quotation specifications.

Identifies:
1. Exact matches (deterministic standardizations and synonymous engineering expressions)
2. Mismatches (incompatible polarity, differing dimensions, voltage conflict, material grade)
3. Missing specifications (RFQ requirement omitted by supplier)
4. Unclear specifications (ambiguous, generic, or conditional values)
5. Additional specifications (supplier quotation offers extra parameters not requested by RFQ)

Ensures that calculations and verifications are deterministic and audited.
"""
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Union

from comparisons.specs.canonical import canonicalize_key
from comparisons.specs.rules import DeterministicSpecMatcher
from comparisons.specs.ai_matcher import AISpecMatcher
from comparisons.specs.schemas import (
    DiscrepancySeverity,
    ItemSpecMatchSummary,
    SingleSpecMatchResult,
    SpecImportance,
    SpecMatchStatus,
    SpecVerdict,
)

logger = logging.getLogger('quoteflow.comparisons.specs.engine')


class SpecificationMatchingEngine:
    """
    Main engine orchestrating technical specification comparison between
    procurement RFQ requirements and supplier quotations.
    """

    def __init__(
        self,
        deterministic_matcher: Optional[DeterministicSpecMatcher] = None,
        ai_matcher: Optional[AISpecMatcher] = None,
    ):
        self.rules = deterministic_matcher or DeterministicSpecMatcher()
        self.ai_matcher = ai_matcher or AISpecMatcher()

    def compare_item_specifications(
        self,
        rfq_item_or_specs: Union[Dict[str, Any], Any],
        supplier_item_or_specs: Union[Dict[str, Any], Any],
        item_name: str = "Quoted Line Item",
        rfq_item_id: Optional[str] = None,
        quotation_item_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        supplier_name: Optional[str] = None,
        use_ai: bool = False,
    ) -> ItemSpecMatchSummary:
        """
        Compares all specifications of an RFQ line item against a supplier quotation line item.

        Args:
            rfq_item_or_specs: Either a dictionary of {param_name: value} or a Django RFQItem instance.
            supplier_item_or_specs: Either a dictionary of {param_name: value} or a Django QuotationItem instance.
            item_name: Display name of the product being matched.
            rfq_item_id: Optional UUID/ID of the RFQItem.
            quotation_item_id: Optional UUID/ID of the QuotationItem.
            supplier_id: Optional UUID/ID of the supplier.
            supplier_name: Optional name of the supplier.
            use_ai: If True, invokes AI semantic matcher when deterministic rules return UNCLEAR.
        """
        # 1. Extract RFQ specifications into normalized canonical dictionary
        rfq_specs = self._extract_rfq_specifications(rfq_item_or_specs)
        
        # 2. Extract Supplier specifications into normalized canonical dictionary
        supplier_specs = self._extract_supplier_specifications(supplier_item_or_specs)

        # Context for reporting and AI
        if hasattr(rfq_item_or_specs, 'item_name'):
            item_name = rfq_item_or_specs.item_name
            rfq_item_id = str(getattr(rfq_item_or_specs, 'id', '')) or rfq_item_id
        if hasattr(supplier_item_or_specs, 'description') or hasattr(supplier_item_or_specs, 'item_description') or hasattr(supplier_item_or_specs, 'item_name'):
            quotation_item_id = str(getattr(supplier_item_or_specs, 'id', '')) or quotation_item_id
            if hasattr(supplier_item_or_specs, 'quotation') and supplier_item_or_specs.quotation:
                supplier = getattr(supplier_item_or_specs.quotation, 'supplier', None)
                if supplier:
                    supplier_id = str(supplier.id)
                    supplier_name = getattr(supplier, 'company_name', getattr(supplier, 'name', 'Unknown Supplier'))

        context = {
            'product_name': item_name,
            'rfq_item_id': rfq_item_id,
            'supplier_name': supplier_name,
        }

        match_results: List[SingleSpecMatchResult] = []
        matched_supplier_keys = set()

        # 3. Iterate over RFQ requirements
        for canon_key, req_data in rfq_specs.items():
            param_name = req_data['name']
            req_value = req_data['value']
            req_unit = req_data.get('unit')
            importance = req_data.get('importance', SpecImportance.MANDATORY)

            # Check if supplier quoted this parameter
            if canon_key not in supplier_specs:
                # 3a. MISSING specification
                # Ancillary or secondary requirements (e.g. inspection certificates, surface finish) are warnings
                if canon_key in ('inspection', 'documentation', 'surface_finish', 'packaging'):
                    severity = DiscrepancySeverity.WARNING
                else:
                    severity = DiscrepancySeverity.CRITICAL if importance == SpecImportance.MANDATORY else DiscrepancySeverity.WARNING
                match_results.append(
                    SingleSpecMatchResult(
                        parameter_name=param_name,
                        canonical_key=canon_key,
                        requirement_value=str(req_value) if req_value is not None else None,
                        requirement_unit=req_unit,
                        supplier_value=None,
                        status=SpecMatchStatus.MISSING,
                        explanation=f"Specification '{param_name}' is required by the RFQ but was omitted from the supplier's quotation.",
                        evidence=None,
                        confidence=1.0,
                        is_deterministic=True,
                        importance=importance,
                        severity=severity,
                    )
                )
                continue

            # Supplier provided this specification
            supp_data = supplier_specs[canon_key]
            supp_value = supp_data['value']
            matched_supplier_keys.add(canon_key)

            # Run deterministic comparison
            det_result = self.rules.match_specification(
                parameter_name=param_name,
                requirement_value=str(req_value),
                supplier_value=str(supp_value),
                requirement_unit=req_unit,
                importance=importance,
            )

            # Check if AI evaluation is permitted and appropriate
            if use_ai and det_result.status == SpecMatchStatus.UNCLEAR:
                logger.debug("Deterministic match unclear for '%s'; invoking AISpecMatcher...", param_name)
                ai_result = self.ai_matcher.evaluate_specification(
                    parameter_name=param_name,
                    requirement_value=str(req_value),
                    supplier_value=str(supp_value),
                    requirement_unit=req_unit,
                    context=context,
                    importance=importance,
                )
                match_results.append(ai_result)
            else:
                match_results.append(det_result)

        # 4. Check for ADDITIONAL specifications offered by supplier not requested in RFQ
        for canon_key, supp_data in supplier_specs.items():
            if canon_key not in rfq_specs and canon_key not in matched_supplier_keys:
                supp_name = supp_data['name']
                supp_val = supp_data['value']
                match_results.append(
                    SingleSpecMatchResult(
                        parameter_name=supp_name,
                        canonical_key=canon_key,
                        requirement_value=None,
                        requirement_unit=None,
                        supplier_value=str(supp_val),
                        status=SpecMatchStatus.ADDITIONAL,
                        explanation=f"Supplier offered additional technical specification '{supp_name}' ({supp_val}) not requested in RFQ.",
                        evidence=str(supp_val),
                        confidence=1.0,
                        is_deterministic=True,
                        importance=SpecImportance.NICE_TO_HAVE,
                        severity=DiscrepancySeverity.INFO,
                    )
                )

        # 5. Aggregate metrics
        total_requirements = len(rfq_specs)
        exact_matches = sum(1 for m in match_results if m.status == SpecMatchStatus.EXACT_MATCH)
        mismatches = sum(1 for m in match_results if m.status == SpecMatchStatus.MISMATCH)
        missing = sum(1 for m in match_results if m.status == SpecMatchStatus.MISSING)
        unclear = sum(1 for m in match_results if m.status == SpecMatchStatus.UNCLEAR)
        additional = sum(1 for m in match_results if m.status == SpecMatchStatus.ADDITIONAL)

        has_critical = any(m.severity == DiscrepancySeverity.CRITICAL for m in match_results)

        # Calculate compliance score
        if total_requirements > 0:
            score = (exact_matches / total_requirements) * 100.0
        else:
            score = 100.0 if not mismatches else 0.0

        # Determine overall verdict
        if mismatches > 0:
            verdict = SpecVerdict.NON_COMPLIANT
        elif missing > 0:
            verdict = SpecVerdict.INCOMPLETE
        elif has_critical:
            verdict = SpecVerdict.NON_COMPLIANT
        elif unclear > 0:
            verdict = SpecVerdict.SPEC_VARIANCE
        elif score >= 100.0:
            verdict = SpecVerdict.COMPLIANT
        else:
            verdict = SpecVerdict.SPEC_VARIANCE

        return ItemSpecMatchSummary(
            item_name=item_name,
            rfq_item_id=rfq_item_id,
            quotation_item_id=quotation_item_id,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            spec_match_score=score,
            total_requirements_count=total_requirements,
            exact_matches_count=exact_matches,
            mismatches_count=mismatches,
            missing_count=missing,
            unclear_count=unclear,
            additional_count=additional,
            has_critical_mismatches=has_critical,
            verdict=verdict,
            matches=match_results,
        )

    def _extract_rfq_specifications(self, rfq_obj_or_specs: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extracts specifications from either a dict or RFQItem model into a canonicalized dictionary.
        Format: { canonical_key: { 'name': orig_name, 'value': val, 'unit': unit, 'importance': enum } }
        """
        results: Dict[str, Dict[str, Any]] = {}

        if isinstance(rfq_obj_or_specs, dict):
            for k, v in rfq_obj_or_specs.items():
                if v is None or str(k).lower() in ('required_spec_summary', 'summary', 'notes', 'description'):
                    continue
                canon = canonicalize_key(str(k))
                if isinstance(v, dict):
                    val = v.get('value')
                    unit = v.get('unit')
                    importance_val = v.get('importance', SpecImportance.MANDATORY)
                    importance = SpecImportance(importance_val) if isinstance(importance_val, str) else importance_val
                else:
                    val = str(v)
                    unit = None
                    importance = SpecImportance.MANDATORY

                results[canon] = {
                    'name': str(k),
                    'value': val,
                    'unit': unit,
                    'importance': importance,
                }
            return results

        # Django RFQItem instance
        # 1. Check custom_specifications JSONField
        custom_specs = getattr(rfq_obj_or_specs, 'custom_specifications', None) or {}
        for k, v in custom_specs.items():
            if str(k).lower() in ('required_spec_summary', 'summary', 'notes', 'description'):
                continue
            if v is not None:
                canon = canonicalize_key(str(k))
                results[canon] = {
                    'name': str(k),
                    'value': str(v),
                    'unit': None,
                    'importance': SpecImportance.MANDATORY,
                }

        # 2. Check relational specifications (RFQItemSpecification)
        spec_rel = getattr(rfq_obj_or_specs, 'specifications', None)
        if spec_rel and hasattr(spec_rel, 'all'):
            for spec in spec_rel.all():
                p_name = getattr(spec, 'parameter_name', '')
                if not p_name:
                    continue
                canon = canonicalize_key(p_name)
                req_val = getattr(spec, 'required_value', '')
                tol = getattr(spec, 'tolerance_or_unit', '')
                imp_str = getattr(spec, 'importance', 'mandatory')
                imp = SpecImportance.MANDATORY
                if imp_str == 'preferred':
                    imp = SpecImportance.PREFERRED
                elif imp_str == 'nice_to_have':
                    imp = SpecImportance.NICE_TO_HAVE

                results[canon] = {
                    'name': p_name,
                    'value': req_val,
                    'unit': tol or None,
                    'importance': imp,
                }

        return results

    def _extract_supplier_specifications(self, supp_obj_or_specs: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extracts specifications from either a dict or QuotationItem model into a canonicalized dictionary.
        Format: { canonical_key: { 'name': orig_name, 'value': val } }
        """
        results: Dict[str, Dict[str, Any]] = {}

        if isinstance(supp_obj_or_specs, dict):
            for k, v in supp_obj_or_specs.items():
                if v is None:
                    continue
                canon = canonicalize_key(str(k))
                val = v.get('value', v) if isinstance(v, dict) else str(v)
                results[canon] = {
                    'name': str(k),
                    'value': val,
                }
            return results

        # Django QuotationItem instance
        # 1. Check specifications JSONField
        specs = getattr(supp_obj_or_specs, 'specifications', None) or {}
        for k, v in specs.items():
            if v is not None:
                canon = canonicalize_key(str(k))
                results[canon] = {
                    'name': str(k),
                    'value': str(v),
                }

        # 2. Check line item quantity field
        qty = getattr(supp_obj_or_specs, 'quantity', None)
        if qty is not None and 'quantity' not in results:
            results['quantity'] = {
                'name': 'Quantity',
                'value': str(int(qty)),
            }

        return results
