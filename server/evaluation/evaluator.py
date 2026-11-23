"""
Quotation AI Extraction Evaluation Engine for QuoteFlow AI.
Implements a multi-dimensional evaluation strategy measuring:
1. Header Metadata Accuracy (Supplier, Dates, Currency, Quote Ref)
2. Financial Numerical Concordance (Subtotal, Tax, Discount, Shipping, Grand Total)
3. Line Item Precision, Recall, and F1 Score (Matching via Description, Qty, Price, Ext Total)
4. Technical Specification Capture Rate
5. Deterministic Validation & Flag Concordance (Arithmetic Inconsistencies, Missing Specs, Risks)
"""

from dataclasses import asdict, dataclass, field
from decimal import Decimal
import difflib
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple


def string_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Computes normalized string similarity ratio [0.0, 1.0]."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    sa = re.sub(r'\s+', ' ', str(a).strip().lower())
    sb = re.sub(r'\s+', ' ', str(b).strip().lower())
    if sa == sb:
        return 1.0
    return difflib.SequenceMatcher(None, sa, sb).ratio()


def float_concordance(expected: Optional[float], actual: Optional[float], tolerance: float = 0.05) -> Tuple[bool, float]:
    """
    Checks if two floating-point values match within absolute or relative tolerance.
    Returns (is_match, absolute_delta).
    """
    if expected is None and actual is None:
        return True, 0.0
    if expected is None or actual is None:
        return False, float('inf')
    delta = abs(float(expected) - float(actual))
    if delta <= tolerance:
        return True, delta
    # Check relative tolerance (0.1%)
    if expected != 0 and (delta / abs(expected)) <= 0.001:
        return True, delta
    return False, delta


@dataclass
class EvaluationMetric:
    name: str
    weight: float
    score: float           # 0.0 to 100.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SingleQuotationEvaluationResult:
    case_id: str
    title: str
    document_format: str
    edge_case_type: str
    header_accuracy: float
    financial_accuracy: float
    line_item_f1: float
    spec_capture_rate: float
    validation_concordance: float
    overall_accuracy_score: float
    is_passed: bool
    summary_notes: List[str] = field(default_factory=list)
    field_breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExtractionEvaluator:
    """
    Evaluates actual extracted quotation outputs against benchmark ground truth.
    """

    WEIGHT_HEADER = 0.15
    WEIGHT_FINANCIAL = 0.25
    WEIGHT_LINE_ITEMS = 0.35
    WEIGHT_SPECS = 0.15
    WEIGHT_VALIDATION = 0.10

    PASSING_THRESHOLD = 85.0  # Percentage required for high-accuracy certification

    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance

    def evaluate(self, ground_truth: Dict[str, Any], extracted: Dict[str, Any]) -> SingleQuotationEvaluationResult:
        """
        Evaluates extracted quotation dictionary against ground truth.
        """
        notes: List[str] = []
        breakdown: Dict[str, Any] = {}

        # 1. Header Metadata Evaluation
        header_score, header_details = self._evaluate_header(
            ground_truth.get("expected_extracted_data", {}),
            extracted
        )
        breakdown["header"] = header_details

        # 2. Financial Totals Evaluation
        fin_score, fin_details = self._evaluate_financials(
            ground_truth.get("expected_extracted_data", {}),
            extracted
        )
        breakdown["financials"] = fin_details

        # 3. Line Items Matching & F1 Score
        line_f1, line_details = self._evaluate_line_items(
            ground_truth.get("expected_extracted_data", {}).get("line_items", []),
            extracted.get("line_items", [])
        )
        breakdown["line_items"] = line_details

        # 4. Technical Specification Capture Rate
        spec_score, spec_details = self._evaluate_specifications(
            ground_truth.get("expected_extracted_data", {}).get("line_items", []),
            extracted.get("line_items", []),
            line_details.get("matches", [])
        )
        breakdown["specifications"] = spec_details

        # 5. Validation Flag Concordance
        val_score, val_details = self._evaluate_validation_concordance(
            ground_truth.get("expected_validation_flags", []),
            extracted.get("validation_flags", [])
        )
        breakdown["validation"] = val_details

        # Compute Overall Weighted Accuracy Score
        overall = (
            header_score * self.WEIGHT_HEADER +
            fin_score * self.WEIGHT_FINANCIAL +
            line_f1 * self.WEIGHT_LINE_ITEMS +
            spec_score * self.WEIGHT_SPECS +
            val_score * self.WEIGHT_VALIDATION
        )
        overall = round(max(0.0, min(100.0, overall)), 2)

        is_passed = overall >= self.PASSING_THRESHOLD
        if is_passed:
            notes.append(f"Passed benchmark criteria ({overall}% >= {self.PASSING_THRESHOLD}%)")
        else:
            notes.append(f"Failed benchmark threshold ({overall}% < {self.PASSING_THRESHOLD}%)")

        return SingleQuotationEvaluationResult(
            case_id=ground_truth["case_id"],
            title=ground_truth.get("title", ground_truth["case_id"]),
            document_format=ground_truth.get("document_format", "PDF"),
            edge_case_type=ground_truth.get("edge_case_type", "STANDARD"),
            header_accuracy=round(header_score, 2),
            financial_accuracy=round(fin_score, 2),
            line_item_f1=round(line_f1, 2),
            spec_capture_rate=round(spec_score, 2),
            validation_concordance=round(val_score, 2),
            overall_accuracy_score=overall,
            is_passed=is_passed,
            summary_notes=notes,
            field_breakdown=breakdown,
        )

    def _evaluate_header(self, exp_data: dict, act_data: dict) -> Tuple[float, dict]:
        exp_supp = exp_data.get("supplier", {})
        act_supp = act_data.get("supplier", {})
        exp_q = exp_data.get("quotation", {})
        act_q = act_data.get("quotation", {})

        checks = {
            "supplier_name": string_similarity(exp_supp.get("supplier_name"), act_supp.get("supplier_name")),
            "quotation_number": 1.0 if (exp_supp.get("quotation_number") or "").strip().lower() == (act_supp.get("quotation_number") or "").strip().lower() else 0.0,
            "quotation_date": 1.0 if exp_q.get("quotation_date") == act_q.get("quotation_date") else 0.0,
            "validity_date": 1.0 if exp_q.get("validity_date") == act_q.get("validity_date") else 0.0,
            "currency": 1.0 if (exp_q.get("currency") or "").upper() == (act_q.get("currency") or "").upper() else 0.0,
        }

        # Handle optional contact fields if present
        if exp_supp.get("email"):
            checks["email"] = 1.0 if exp_supp.get("email", "").lower() in (act_supp.get("email") or "").lower() else 0.0

        score = (sum(checks.values()) / len(checks)) * 100.0
        return score, checks

    def _evaluate_financials(self, exp_data: dict, act_data: dict) -> Tuple[float, dict]:
        exp_q = exp_data.get("quotation", {})
        act_q = act_data.get("quotation", {})

        fields = ["subtotal", "tax", "grand_total"]
        if exp_q.get("discount", 0) > 0:
            fields.append("discount")
        if exp_q.get("shipping", 0) > 0:
            fields.append("shipping")

        checks = {}
        matched_count = 0

        for f in fields:
            exp_val = exp_q.get(f)
            act_val = act_q.get(f)
            matched, delta = float_concordance(exp_val, act_val, tolerance=self.tolerance)
            checks[f] = {
                "expected": exp_val,
                "actual": act_val,
                "matched": matched,
                "delta": delta,
            }
            if matched:
                matched_count += 1

        score = (matched_count / len(fields)) * 100.0 if fields else 100.0
        return score, checks

    def _evaluate_line_items(self, exp_items: List[dict], act_items: List[dict]) -> Tuple[float, dict]:
        """
        Bipartite matching of line items using description similarity and numerical checks.
        Computes precision, recall, and F1 score.
        """
        if not exp_items and not act_items:
            return 100.0, {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matches": []}
        if not exp_items or not act_items:
            return 0.0, {"precision": 0.0, "recall": 0.0, "f1": 0.0, "matches": []}

        matched_pairs = []
        used_act_indices = set()

        for exp_idx, exp_item in enumerate(exp_items):
            best_match_idx = None
            best_match_score = -1.0

            for act_idx, act_item in enumerate(act_items):
                if act_idx in used_act_indices:
                    continue

                desc_sim = string_similarity(exp_item.get("description"), act_item.get("description"))
                qty_match, _ = float_concordance(exp_item.get("quantity"), act_item.get("quantity"), tolerance=0.01)
                price_match, _ = float_concordance(exp_item.get("unit_price"), act_item.get("unit_price"), tolerance=self.tolerance)
                total_match, _ = float_concordance(exp_item.get("total"), act_item.get("total"), tolerance=self.tolerance)

                # Composite item match score
                match_score = (desc_sim * 0.4) + (0.2 if qty_match else 0.0) + (0.2 if price_match else 0.0) + (0.2 if total_match else 0.0)

                if match_score > best_match_score and match_score >= 0.65:
                    best_match_score = match_score
                    best_match_idx = act_idx

            if best_match_idx is not None:
                used_act_indices.add(best_match_idx)
                matched_pairs.append({
                    "expected_index": exp_idx,
                    "actual_index": best_match_idx,
                    "score": best_match_score,
                })

        true_positives = len(matched_pairs)
        precision = true_positives / len(act_items) if act_items else 0.0
        recall = true_positives / len(exp_items) if exp_items else 0.0
        f1 = (2 * precision * recall / (precision + recall)) * 100.0 if (precision + recall) > 0 else 0.0

        return f1, {
            "expected_count": len(exp_items),
            "actual_count": len(act_items),
            "true_positives": true_positives,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 2),
            "matches": matched_pairs,
        }

    def _evaluate_specifications(self, exp_items: List[dict], act_items: List[dict], matches: List[dict]) -> Tuple[float, dict]:
        """
        Evaluates technical specifications extracted within matched line items.
        """
        total_exp_specs = 0
        total_matched_specs = 0

        for match in matches:
            exp_item = exp_items[match["expected_index"]]
            act_item = act_items[match["actual_index"]]

            exp_specs = exp_item.get("specifications", [])
            act_specs = act_item.get("specifications", [])
            total_exp_specs += len(exp_specs)

            for exp_s in exp_specs:
                exp_name = exp_s.get("name", "").strip().lower()
                exp_val = exp_s.get("value", "").strip().lower()

                for act_s in act_specs:
                    act_name = act_s.get("name", "").strip().lower()
                    act_val = act_s.get("value", "").strip().lower()

                    if (string_similarity(exp_name, act_name) >= 0.75 and
                            string_similarity(exp_val, act_val) >= 0.75):
                        total_matched_specs += 1
                        break

        # Edge case: If quotation legitimately has zero expected specs (e.g. Case 8)
        if total_exp_specs == 0:
            # If actual also extracted 0, 100% correct
            actual_total_specs = sum(len(item.get("specifications", [])) for item in act_items)
            score = 100.0 if actual_total_specs == 0 else 50.0
        else:
            score = (total_matched_specs / total_exp_specs) * 100.0

        return score, {
            "expected_spec_count": total_exp_specs,
            "matched_spec_count": total_matched_specs,
        }

    def _evaluate_validation_concordance(self, exp_flags: List[dict], act_flags: List[dict]) -> Tuple[float, dict]:
        """
        Evaluates whether deterministic validation detected the expected flags.
        """
        exp_types = {f["flag_type"] for f in exp_flags}
        act_types = set()
        for f in act_flags:
            if isinstance(f, dict):
                act_types.add(f.get("flag_type") or f.get("type"))
            elif hasattr(f, "flag_type"):
                act_types.add(f.flag_type)

        if not exp_types and not act_types:
            return 100.0, {"expected_flags": [], "actual_flags": [], "concordance": 1.0}

        intersection = exp_types.intersection(act_types)
        union = exp_types.union(act_types)
        jaccard = (len(intersection) / len(union)) * 100.0 if union else 100.0

        return jaccard, {
            "expected_types": list(exp_types),
            "actual_types": list(act_types),
            "matched_types": list(intersection),
            "jaccard_similarity": round(jaccard, 2),
        }
