"""
Deterministic Specification Comparison Rules for Industrial Procurement.
Implements authoritative engineering evaluation rules for electrical polarity (PNP/NPN),
voltage ranges, sensing distances, connector standards (M12/M8), IP ratings, and materials.
"""
from decimal import Decimal
import re
from typing import Optional, Tuple

from .canonical import (
    canonicalize_parameter_key,
    clean_spec_value,
    extract_connection_tokens,
    normalize_voltage,
    parse_distance_dimension,
    parse_ip_rating,
)
from .schemas import (
    DiscrepancySeverity,
    SingleSpecMatchResult,
    SpecImportance,
    SpecMatchStatus,
)


class DeterministicSpecMatcher:
    """
    Evaluates specification pairs using deterministic engineering domain rules.
    Returns SingleSpecMatchResult if deterministically resolved, or None if
    semantic analysis (AI assistance) is required.
    """

    AMBIGUOUS_PLACEHOLDERS = {
        'standard', 'std', 'tbd', 'tba', 'varies', 'custom', 'see datasheet',
        'as per catalog', 'consult factory', 'per standard', 'optional',
    }

    @classmethod
    def match_specification(
        cls,
        parameter_name: str,
        requirement_value: str,
        supplier_value: str,
        requirement_unit: Optional[str] = None,
        importance: SpecImportance = SpecImportance.MANDATORY,
        evidence: Optional[str] = None,
    ) -> SingleSpecMatchResult:
        """
        Attempts to deterministically match requirement vs supplier value.
        """
        canonical_key = canonicalize_parameter_key(parameter_name)
        req_clean = clean_spec_value(requirement_value)
        sup_clean = clean_spec_value(supplier_value)

        # 1. Missing Value Check
        if not sup_clean:
            return SingleSpecMatchResult(
                parameter_name=parameter_name,
                canonical_key=canonical_key,
                requirement_value=req_clean,
                requirement_unit=requirement_unit,
                supplier_value=None,
                status=SpecMatchStatus.MISSING,
                explanation=f"Required specification '{parameter_name}' was not stated in the supplier quotation.",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL if importance == SpecImportance.MANDATORY else DiscrepancySeverity.WARNING,
            )

        # 2. Check for Ambiguous / Generic Supplier Placeholders
        sup_lower = sup_clean.lower()
        if any(ph in sup_lower for ph in cls.AMBIGUOUS_PLACEHOLDERS):
            return SingleSpecMatchResult(
                parameter_name=parameter_name,
                canonical_key=canonical_key,
                requirement_value=req_clean,
                requirement_unit=requirement_unit,
                supplier_value=sup_clean,
                status=SpecMatchStatus.UNCLEAR,
                explanation=(
                    f"Supplier specified generic/ambiguous value '{sup_clean}' for '{parameter_name}'. "
                    f"Does not confirm exact compliance with required '{req_clean}'."
                ),
                evidence=evidence or sup_clean,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.WARNING,
            )

        # 3. Exact Literal / Normalized String Match
        if req_clean.lower() == sup_clean.lower():
            return SingleSpecMatchResult(
                parameter_name=parameter_name,
                canonical_key=canonical_key,
                requirement_value=req_clean,
                supplier_value=sup_clean,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=f"Specification '{parameter_name}' matches exactly ({req_clean}).",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        # 4. Domain-Specific Engineering Dispatch
        if canonical_key == 'output':
            return cls._match_output_polarity(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)

        if canonical_key == 'output_function':
            return cls._match_contact_function(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)

        if canonical_key == 'voltage':
            return cls._match_voltage(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)

        if canonical_key in ('sensing_distance', 'dimensions', 'housing_size', 'length'):
            dist_res = cls._match_distance(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)
            if dist_res is not None:
                return dist_res

        if canonical_key in ('accuracy', 'tolerance'):
            r_tol = re.sub(r'[^0-9\.]', '', req_clean)
            s_tol = re.sub(r'[^0-9\.]', '', sup_clean)
            if r_tol and s_tol and r_tol == s_tol:
                return SingleSpecMatchResult(
                    parameter_name=parameter_name,
                    canonical_key=canonical_key,
                    requirement_value=req_clean,
                    requirement_unit=requirement_unit,
                    supplier_value=sup_clean,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Tolerance matches requirement ({sup_clean}).",
                    evidence=evidence or sup_clean,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )

        if canonical_key in ('inspection', 'documentation'):
            r_insp = req_clean.upper()
            s_insp = sup_clean.upper()
            if ('INSPECTION' in r_insp or 'CERTIFICATE' in r_insp or 'REPORT' in r_insp) and \
               ('INSPECTION' in s_insp or 'CERTIFICATE' in s_insp or 'REPORT' in s_insp):
                return SingleSpecMatchResult(
                    parameter_name=parameter_name,
                    canonical_key=canonical_key,
                    requirement_value=req_clean,
                    requirement_unit=requirement_unit,
                    supplier_value=sup_clean,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Inspection & documentation requirement satisfied ({sup_clean}).",
                    evidence=evidence or sup_clean,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )

        if canonical_key == 'quantity':
            r_num = re.sub(r'[^0-9]', '', req_clean)
            s_num = re.sub(r'[^0-9]', '', sup_clean)
            if r_num and s_num and int(r_num) == int(s_num):
                return SingleSpecMatchResult(
                    parameter_name=parameter_name,
                    canonical_key=canonical_key,
                    requirement_value=req_clean,
                    requirement_unit=requirement_unit,
                    supplier_value=sup_clean,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Line item batch quantity matches requirement ({sup_clean} units).",
                    evidence=evidence or sup_clean,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )

        if canonical_key in ('process', 'manufacturing_process'):
            r_proc = req_clean.upper()
            s_proc = sup_clean.upper()
            if ('TURNING' in r_proc and 'TURNING' in s_proc) or ('CNC' in r_proc and 'CNC' in s_proc):
                return SingleSpecMatchResult(
                    parameter_name=parameter_name,
                    canonical_key=canonical_key,
                    requirement_value=req_clean,
                    requirement_unit=requirement_unit,
                    supplier_value=sup_clean,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Manufacturing process matches ({sup_clean}).",
                    evidence=evidence or sup_clean,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )

        if canonical_key == 'connection':
            conn_res = cls._match_connection(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)
            if conn_res is not None:
                return conn_res

        if canonical_key == 'ip_rating':
            ip_res = cls._match_ip_rating(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)
            if ip_res is not None:
                return ip_res

        if canonical_key == 'material':
            mat_res = cls._match_material(parameter_name, canonical_key, req_clean, sup_clean, importance, evidence)
            if mat_res is not None:
                return mat_res

        # If deterministic rules cannot conclusively establish equivalence or mismatch, return UNCLEAR
        return SingleSpecMatchResult(
            parameter_name=parameter_name,
            canonical_key=canonical_key,
            requirement_value=req_clean,
            requirement_unit=requirement_unit,
            supplier_value=sup_clean,
            status=SpecMatchStatus.UNCLEAR,
            explanation=f"Specification variance between '{req_clean}' and '{sup_clean}'. Unable to deterministically confirm equivalence without semantic evaluation.",
            evidence=evidence or sup_clean,
            confidence=0.5,
            is_deterministic=True,
            importance=importance,
            severity=DiscrepancySeverity.WARNING,
        )

    @classmethod
    def _match_output_polarity(
        cls, param_name, key, req, sup, importance, evidence
    ) -> SingleSpecMatchResult:
        """
        Evaluates switching output polarities:
        PNP (sourcing) vs NPN (sinking) vs Push-Pull.
        """
        r_upper = req.upper()
        s_upper = sup.upper()

        is_req_pnp = 'PNP' in r_upper
        is_req_npn = 'NPN' in r_upper
        is_sup_pnp = 'PNP' in s_upper
        is_sup_npn = 'NPN' in s_upper
        is_sup_push_pull = 'PUSH-PULL' in s_upper or 'PUSH PULL' in s_upper

        if is_req_pnp and is_sup_npn and not is_sup_pnp:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.MISMATCH,
                explanation=(
                    "Requirement specifies PNP output, but supplier quoted NPN output. "
                    "PNP switches positive voltage (current sourcing), while NPN switches ground (current sinking). "
                    "These electrical switching polarities are incompatible with PLC inputs expecting PNP."
                ),
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL,
            )

        if is_req_npn and is_sup_pnp and not is_sup_npn:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.MISMATCH,
                explanation=(
                    "Requirement specifies NPN output, but supplier quoted PNP output. "
                    "NPN switches ground (current sinking), while PNP switches positive voltage (current sourcing). "
                    "These polarities are electrically incompatible."
                ),
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL,
            )

        if (is_req_pnp or is_req_npn) and is_sup_push_pull:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=(
                    f"Supplier quoted Push-Pull output, which is fully compatible with the requested {r_upper} "
                    f"and automatically supports both sourcing and sinking wiring."
                ),
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        if (is_req_pnp and is_sup_pnp) or (is_req_npn and is_sup_npn):
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=f"Output polarity matches exactly ({sup}).",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        return SingleSpecMatchResult(
            parameter_name=param_name,
            canonical_key=key,
            requirement_value=req,
            supplier_value=sup,
            status=SpecMatchStatus.MISMATCH,
            explanation=f"Output specification mismatch: required '{req}', supplier quoted '{sup}'.",
            evidence=evidence,
            confidence=1.0,
            is_deterministic=True,
            importance=importance,
            severity=DiscrepancySeverity.CRITICAL,
        )

    @classmethod
    def _match_contact_function(cls, param_name, key, req, sup, importance, evidence) -> SingleSpecMatchResult:
        """Normally Open (NO) vs Normally Closed (NC) vs Antivalent (NO+NC)."""
        r_upper = req.upper()
        s_upper = sup.upper()

        # Check for complementary / antivalent contacts that satisfy either NO or NC requirement
        is_complementary = (
            ('NO' in s_upper and 'NC' in s_upper)
            or 'NO/NC' in s_upper
            or 'NO+NC' in s_upper
            or 'NO + NC' in s_upper
            or 'ANTIVALENT' in s_upper
            or 'CHANGEOVER' in s_upper
        )
        if ('NO' in r_upper or 'NC' in r_upper) and is_complementary:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=f"Supplier quoted complementary contact ({sup}) which satisfies the required {r_upper}.",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        if ('NO' in r_upper or 'NORMALLY OPEN' in r_upper) and ('NC' in s_upper or 'NORMALLY CLOSED' in s_upper):
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.MISMATCH,
                explanation="Contact logic mismatch: required Normally Open (NO), but supplier quoted Normally Closed (NC).",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL,
            )

        return SingleSpecMatchResult(
            parameter_name=param_name,
            canonical_key=key,
            requirement_value=req,
            supplier_value=sup,
            status=SpecMatchStatus.MISMATCH,
            explanation=f"Contact function mismatch: required '{req}', supplier quoted '{sup}'.",
            evidence=evidence,
            confidence=1.0,
            is_deterministic=True,
            importance=importance,
            severity=DiscrepancySeverity.WARNING,
        )

    @classmethod
    def _match_voltage(cls, param_name, key, req, sup, importance, evidence) -> SingleSpecMatchResult:
        """Operating voltage and AC/DC standard matching."""
        r_norm = normalize_voltage(req)
        s_norm = normalize_voltage(sup)

        if r_norm and s_norm:
            if r_norm == s_norm:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Voltage matches exactly ({r_norm}).",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )

            # AC vs DC conflict check
            if ('DC' in r_norm and 'AC' in s_norm) or ('AC' in r_norm and 'DC' in s_norm):
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.MISMATCH,
                    explanation=f"Power source type mismatch: required {r_norm}, but supplier quoted {s_norm}. AC and DC are incompatible.",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.CRITICAL,
                )

            # Wide operating range check: e.g. req "24V DC", sup "10-30V DC"
            range_match = re.match(r'([0-9]+)-([0-9]+)V\s*(DC|AC)?', s_norm)
            fixed_match = re.match(r'([0-9]+)V\s*(DC|AC)?', r_norm)
            if range_match and fixed_match:
                min_v = int(range_match.group(1))
                max_v = int(range_match.group(2))
                target_v = int(fixed_match.group(1))
                req_type = fixed_match.group(2) or ''
                sup_type = range_match.group(3) or ''

                if (not req_type or not sup_type or req_type == sup_type) and min_v <= target_v <= max_v:
                    return SingleSpecMatchResult(
                        parameter_name=param_name,
                        canonical_key=key,
                        requirement_value=req,
                        supplier_value=sup,
                        status=SpecMatchStatus.EXACT_MATCH,
                        explanation=f"Required voltage {r_norm} is fully within supplier's operating range ({s_norm}).",
                        evidence=evidence,
                        confidence=1.0,
                        is_deterministic=True,
                        importance=importance,
                        severity=DiscrepancySeverity.NONE,
                    )

            # Distinct voltages mismatch
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.MISMATCH,
                explanation=f"Voltage mismatch: required {r_norm}, but supplier quoted {s_norm}.",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL,
            )

        return None

    @classmethod
    def _match_distance(cls, param_name, key, req, sup, importance, evidence) -> Optional[SingleSpecMatchResult]:
        """Sensing distance or dimension matching with mm unit normalization."""
        r_dist = parse_distance_dimension(req)
        s_dist = parse_distance_dimension(sup)

        if r_dist and s_dist:
            r_val, r_unit = r_dist
            s_val, s_unit = s_dist

            if r_unit == s_unit and r_val == s_val:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"{param_name} matches exactly ({r_val} {r_unit}).",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )
            else:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.MISMATCH,
                    explanation=f"{param_name} mismatch: required {r_val} {r_unit}, but supplier quoted {s_val} {s_unit}.",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.WARNING if key == 'sensing_distance' else DiscrepancySeverity.CRITICAL,
                )

        return None

    @classmethod
    def _match_connection(cls, param_name, key, req, sup, importance, evidence) -> Optional[SingleSpecMatchResult]:
        """Electrical connection and standard connector matching (e.g. M12, M8, Cable)."""
        r_tokens = extract_connection_tokens(req)
        s_tokens = extract_connection_tokens(sup)

        if r_tokens and s_tokens:
            # Check main connector standard
            standards = {'M12', 'M8', 'M5', 'M18', 'M30', 'CABLE'}
            r_std = r_tokens.intersection(standards)
            s_std = s_tokens.intersection(standards)

            if r_std and s_std and r_std == s_std:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Connection standard matches exactly ({list(r_std)[0]}).",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )
            elif r_std and s_std and r_std != s_std:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.MISMATCH,
                    explanation=f"Connection mismatch: required {list(r_std)[0]}, but supplier quoted {list(s_std)[0]}.",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.CRITICAL,
                )

        return None

    @classmethod
    def _match_ip_rating(cls, param_name, key, req, sup, importance, evidence) -> Optional[SingleSpecMatchResult]:
        """IP Ingress Protection rating verification (e.g. IP67 vs IP68 or IP65)."""
        r_ip = parse_ip_rating(req)
        s_ip = parse_ip_rating(sup)

        if r_ip and s_ip:
            r_solids, r_liquids = r_ip
            s_solids, s_liquids = s_ip

            if s_solids == r_solids and s_liquids == r_liquids:
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Ingress protection rating matches exactly (IP{s_solids}{s_liquids}).",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )
            elif s_solids >= r_solids and s_liquids >= r_liquids:
                # Strictly superior
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.EXACT_MATCH,
                    explanation=f"Supplier quoted IP{s_solids}{s_liquids}, which exceeds required IP{r_solids}{r_liquids}.",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.NONE,
                )
            else:
                # Inferior
                return SingleSpecMatchResult(
                    parameter_name=param_name,
                    canonical_key=key,
                    requirement_value=req,
                    supplier_value=sup,
                    status=SpecMatchStatus.MISMATCH,
                    explanation=f"Ingress protection deficit: required IP{r_solids}{r_liquids}, but supplier quoted inferior IP{s_solids}{s_liquids} (insufficient liquid ingress protection).",
                    evidence=evidence,
                    confidence=1.0,
                    is_deterministic=True,
                    importance=importance,
                    severity=DiscrepancySeverity.WARNING,
                )

        return None

    @classmethod
    def _match_material(cls, param_name, key, req, sup, importance, evidence) -> Optional[SingleSpecMatchResult]:
        """Stainless steel grades and metallic/plastic material matching."""
        r_up = req.upper()
        s_up = sup.upper()

        # Grade 316 vs 304 conflict
        is_316_req = '316' in r_up
        is_304_sup = '304' in s_up
        if is_316_req and is_304_sup and '316' not in s_up:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.MISMATCH,
                explanation=(
                    "Material grade mismatch: RFQ requires Stainless Steel 316/316L (molybdenum-alloyed), "
                    "but supplier quoted Grade 304. Grade 304 lacks chemical/salt corrosion resistance."
                ),
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.CRITICAL,
            )

        # 316 vs 316L match
        if ('316L' in r_up and '316L' in s_up) or ('316' in r_up and '316' in s_up):
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=f"Material grade matches ({sup}).",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        # EN8 carbon steel match (e.g. EN8 Steel vs EN8 Medium Carbon Steel)
        if 'EN8' in r_up and 'EN8' in s_up:
            return SingleSpecMatchResult(
                parameter_name=param_name,
                canonical_key=key,
                requirement_value=req,
                supplier_value=sup,
                status=SpecMatchStatus.EXACT_MATCH,
                explanation=f"Material grade matches EN8 carbon steel ({sup}).",
                evidence=evidence,
                confidence=1.0,
                is_deterministic=True,
                importance=importance,
                severity=DiscrepancySeverity.NONE,
            )

        return None
