"""
Comprehensive Test Suite for QuoteFlow AI 10-Case Benchmark Testing Dataset & Evaluation Engine.
Tests:
- Ground truth integrity & schema validity
- Document generators for all 10 formats & edge cases
- Evaluator scoring accuracy (exact match, perturbation penalty, F1-scores)
- Integration with deterministic validation engine (arithmetic discrepancies, missing specs)
- Integration with specification matching and risk evaluation engines
"""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from evaluation.dataset.ground_truth import DATASET_GROUND_TRUTH, get_ground_truth_by_case_id
from evaluation.dataset.generator import DOCS_DIR, generate_all_benchmark_documents
from evaluation.evaluator import ExtractionEvaluator, float_concordance, string_similarity
from evaluation.runner import BenchmarkRunner
from extractions.validation import (
    QuotationDeterministicValidator,
    ValidationFlagType,
    ValidationSeverity,
)
from comparisons.specs.engine import SpecificationMatchingEngine
from comparisons.specs.schemas import SpecVerdict
from comparisons.risk.engine import QuotationRiskEngine


class BenchmarkDatasetIntegrityTests(SimpleTestCase):
    """Tests the structure, schema, and completeness of the 10 benchmark cases."""

    def test_ten_cases_present(self):
        self.assertEqual(len(DATASET_GROUND_TRUTH), 10)

    def test_expected_case_ids(self):
        expected_ids = [
            "case_01_clean_pdf",
            "case_02_messy_pdf",
            "case_03_excel",
            "case_04_scanned_pdf",
            "case_05_multi_item_bom",
            "case_06_compound_tax",
            "case_07_tiered_discounts",
            "case_08_missing_specs",
            "case_09_mismatched_totals",
            "case_10_risky_commercial_terms",
        ]
        actual_ids = [c["case_id"] for c in DATASET_GROUND_TRUTH]
        self.assertEqual(actual_ids, expected_ids)

    def test_ground_truth_lookup_helper(self):
        case1 = get_ground_truth_by_case_id("case_01_clean_pdf")
        self.assertEqual(case1["case_id"], "case_01_clean_pdf")
        self.assertEqual(case1["document_format"], "PDF")

        with self.assertRaises(KeyError):
            get_ground_truth_by_case_id("non_existent_case")

    def test_required_ground_truth_keys(self):
        for case in DATASET_GROUND_TRUTH:
            self.assertIn("case_id", case)
            self.assertIn("file_name", case)
            self.assertIn("document_format", case)
            self.assertIn("edge_case_type", case)
            self.assertIn("expected_extracted_data", case)
            self.assertIn("expected_calculations", case)
            self.assertIn("expected_validation_flags", case)
            self.assertIn("expected_spec_matching", case)
            self.assertIn("expected_risk_flags", case)

            ext = case["expected_extracted_data"]
            self.assertIn("supplier", ext)
            self.assertIn("quotation", ext)
            self.assertIn("commercial_terms", ext)
            self.assertIn("line_items", ext)
            self.assertGreater(len(ext["line_items"]), 0)


class DocumentGenerationTests(SimpleTestCase):
    """Verifies that all 10 realistic test documents generate correctly and are readable."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.generated_files = generate_all_benchmark_documents()

    def test_all_ten_documents_generated(self):
        self.assertEqual(len(self.generated_files), 10)
        for f in self.generated_files:
            self.assertTrue(f.exists(), f"File {f.name} does not exist.")
            self.assertGreater(f.stat().st_size, 0, f"File {f.name} is empty.")

    def test_excel_document_structure(self):
        excel_path = DOCS_DIR / "03_excel_quotation_nexus.xlsx"
        self.assertTrue(excel_path.exists())
        import openpyxl
        wb = openpyxl.load_workbook(str(excel_path), data_only=False)
        self.assertIn("Price Quotation", wb.sheetnames)
        self.assertIn("Technical Data", wb.sheetnames)
        ws = wb["Price Quotation"]
        self.assertEqual(ws["A1"].value, "Nexus Industrial Systems GmbH")
        # Check that formula was written
        formula_found = any("SUM" in str(cell.value) for row in ws.iter_rows(values_only=False) for cell in row if cell.value)
        self.assertTrue(formula_found)


class EvaluatorEngineTests(SimpleTestCase):
    """Verifies accuracy scoring formulas, F1 matching, and tolerance thresholds."""

    def setUp(self):
        self.evaluator = ExtractionEvaluator(tolerance=0.05)

    def test_string_similarity(self):
        self.assertEqual(string_similarity("Apex Precision", "Apex Precision"), 1.0)
        self.assertEqual(string_similarity("Apex Precision", "apex precision"), 1.0)
        self.assertGreater(string_similarity("Apex Precision Inc.", "Apex Precision Ltd."), 0.75)
        self.assertEqual(string_similarity("", ""), 1.0)
        self.assertEqual(string_similarity("Apex", ""), 0.0)

    def test_float_concordance(self):
        matched, delta = float_concordance(100.0, 100.02, tolerance=0.05)
        self.assertTrue(matched)
        self.assertAlmostEqual(delta, 0.02)

        matched, delta = float_concordance(100.0, 105.0, tolerance=0.05)
        self.assertFalse(matched)

    def test_perfect_evaluation_scores_hundred(self):
        case = get_ground_truth_by_case_id("case_01_clean_pdf")
        result = self.evaluator.evaluate(case, {
            **case["expected_extracted_data"],
            "validation_flags": case["expected_validation_flags"],
        })
        self.assertEqual(result.overall_accuracy_score, 100.0)
        self.assertTrue(result.is_passed)
        self.assertEqual(result.header_accuracy, 100.0)
        self.assertEqual(result.financial_accuracy, 100.0)
        self.assertEqual(result.line_item_f1, 100.0)

    def test_perturbed_extraction_penalized(self):
        case = get_ground_truth_by_case_id("case_01_clean_pdf")
        perturbed_data = {
            **case["expected_extracted_data"],
            "quotation": {
                **case["expected_extracted_data"]["quotation"],
                "subtotal": 500.00,  # Corrupted subtotal ($950 -> $500)
            },
            "line_items": [],  # Dropped item!
            "validation_flags": [],
        }
        result = self.evaluator.evaluate(case, perturbed_data)
        self.assertLess(result.overall_accuracy_score, 85.0)
        self.assertLess(result.financial_accuracy, 100.0)
        self.assertLess(result.line_item_f1, 100.0)

    def test_benchmark_runner_full_suite(self):
        runner = BenchmarkRunner(self.evaluator)
        results = runner.run_benchmark()
        self.assertEqual(len(results), 10)
        for r in results:
            self.assertTrue(r.is_passed)
            self.assertEqual(r.overall_accuracy_score, 100.0)


class DeterministicValidationDatasetTests(SimpleTestCase):
    """
    Tests that running QuoteFlow AI's actual deterministic validation engine
    against the 10 benchmark test cases generates the exact expected flags and math reconciliations.
    """

    def test_case_01_clean_pdf_is_math_consistent(self):
        case = get_ground_truth_by_case_id("case_01_clean_pdf")
        report = QuotationDeterministicValidator.validate(case["expected_extracted_data"])
        self.assertTrue(report.is_valid)
        self.assertTrue(report.is_math_consistent)
        self.assertEqual(float(report.calculated_items_subtotal), 950.00)
        self.assertEqual(float(report.calculated_tax_total), 76.00)
        self.assertEqual(float(report.calculated_grand_total), 1026.00)
        self.assertEqual(len([f for f in report.flags if f.severity == ValidationSeverity.ERROR]), 0)

    def test_case_09_mismatched_totals_detected(self):
        """Case 9 contains an intentional arithmetic discrepancy on printed invoice."""
        case = get_ground_truth_by_case_id("case_09_mismatched_totals")
        report = QuotationDeterministicValidator.validate(case["expected_extracted_data"])
        self.assertFalse(report.is_math_consistent)
        self.assertTrue(report.has_errors)

        flag_types = [f.flag_type for f in report.flags]
        self.assertIn(ValidationFlagType.SUBTOTAL_INCONSISTENCY.value, flag_types)

        # Check calculated vs stated discrepancy
        self.assertEqual(float(report.calculated_items_subtotal), 1000.00)
        self.assertEqual(report.flags[0].expected_value, 1000.00)
        self.assertEqual(report.flags[0].actual_value, 900.00)

    def test_case_08_missing_specifications_flagged(self):
        """Case 8 omits critical engineering specs / substitutes MS for EN8."""
        case = get_ground_truth_by_case_id("case_08_missing_specs")
        report = QuotationDeterministicValidator.validate(case["expected_extracted_data"])
        self.assertTrue(report.is_valid)


class SpecificationAndRiskEngineDatasetTests(SimpleTestCase):
    """
    Tests technical specification matching and risk rule evaluation against benchmark cases.
    """

    def setUp(self):
        self.spec_engine = SpecificationMatchingEngine()
        self.risk_engine = QuotationRiskEngine()

    def test_case_01_spec_matching_exact(self):
        case = get_ground_truth_by_case_id("case_01_clean_pdf")
        rfq_req = {
            "Material": "EN8 Medium Carbon Steel",
            "Finished Diameter": "40 mm",
            "Overall Length": "500 mm",
            "Dimensional Tolerance": "±0.05 mm",
        }
        item_specs = {s["name"]: s["value"] for s in case["expected_extracted_data"]["line_items"][0]["specifications"]}
        summary = self.spec_engine.compare_item_specifications(rfq_req, item_specs, item_name="Custom Industrial Shaft")
        self.assertIn(summary.verdict, [SpecVerdict.COMPLIANT, SpecVerdict.SPEC_VARIANCE])
        self.assertGreaterEqual(float(summary.spec_match_score), 95.0)

    def test_case_10_commercial_risk_flags_triggered(self):
        """Case 10 has 100% advance, 20 weeks delivery, 15 days warranty."""
        case = get_ground_truth_by_case_id("case_10_risky_commercial_terms")
        quote_data = {
            **case["expected_extracted_data"]["quotation"],
            **case["expected_extracted_data"]["commercial_terms"],
            "supplier_name": case["expected_extracted_data"]["supplier"]["supplier_name"],
            "items": case["expected_extracted_data"]["line_items"],
        }
        rfq_data = {
            "required_delivery_date": None,
            "target_budget": 1000.0,
            "delivery_weeks_target": 3,
        }
        report = self.risk_engine.evaluate_quotation(quote_data, rfq_data)
        flag_types = [f.type.value if hasattr(f.type, 'value') else str(f.type) for f in report.flags]

        # Must flag payment risk (100% advance)
        self.assertTrue(any("PAYMENT" in ft.upper() for ft in flag_types), f"Payment risk missing: {flag_types}")
        # Must flag warranty risk (15 days)
        self.assertTrue(any("WARRANTY" in ft.upper() for ft in flag_types), f"Warranty risk missing: {flag_types}")
