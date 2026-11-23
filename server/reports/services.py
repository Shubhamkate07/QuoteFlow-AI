"""
Services for generating procurement reports, PDF renders, and Excel workbooks.
"""
from typing import Any, Dict, Optional
import io
import openpyxl

from .excel_generator import RFQComparisonExcelGenerator
from .pdf_generator import RFQComparisonPDFGenerator


def generate_rfq_comparison_excel_workbook(
    rfq,
    comparison_data: Optional[Dict[str, Any]] = None,
    user=None,
    organization=None,
) -> openpyxl.Workbook:
    """
    Generates an openpyxl Workbook instance for the given RFQ comparison data.
    """
    generator = RFQComparisonExcelGenerator(
        rfq=rfq,
        comparison_data=comparison_data,
        user=user,
        organization=organization,
    )
    return generator.generate_workbook()


def generate_rfq_comparison_excel_bytes(
    rfq,
    comparison_data: Optional[Dict[str, Any]] = None,
    user=None,
    organization=None,
) -> io.BytesIO:
    """
    Generates an in-memory BytesIO buffer containing the Excel (.xlsx) report.
    """
    generator = RFQComparisonExcelGenerator(
        rfq=rfq,
        comparison_data=comparison_data,
        user=user,
        organization=organization,
    )
    return generator.generate_bytes()


def generate_rfq_comparison_pdf_bytes(
    rfq,
    comparison_data: Optional[Dict[str, Any]] = None,
    user=None,
    organization=None,
) -> io.BytesIO:
    """
    Generates an in-memory BytesIO buffer containing the professional PDF comparison report.
    """
    generator = RFQComparisonPDFGenerator(
        rfq=rfq,
        comparison_data=comparison_data,
        user=user,
        organization=organization,
    )
    return generator.generate_bytes()


def generate_rfq_comparison_pdf_document(
    rfq,
    comparison_data: Optional[Dict[str, Any]] = None,
    user=None,
    organization=None,
) -> bytes:
    """
    Returns raw PDF bytes for the RFQ comparison report.
    """
    buffer = generate_rfq_comparison_pdf_bytes(
        rfq=rfq,
        comparison_data=comparison_data,
        user=user,
        organization=organization,
    )
    return buffer.getvalue()

