"""
Excel spreadsheet text extraction engine using openpyxl.
Supports multi-worksheet parsing, sheet name preservation, cell type conversions,
empty cell alignment, and tabular markdown generation.
"""

import io
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from .base import BaseDocumentExtractor, DocumentExtractionResult, SheetExtraction
from .exceptions import CorruptDocumentError, EmptyDocumentError


class ExcelExtractor(BaseDocumentExtractor):
    """
    Extracts structured data, sheet names, cell grids, and text from Excel XLSX spreadsheets using openpyxl.
    """

    def __init__(
        self,
        max_rows_per_sheet: int = 5000,
        max_cols_per_sheet: int = 100,
        skip_empty_rows: bool = True,
    ):
        self.max_rows_per_sheet = max_rows_per_sheet
        self.max_cols_per_sheet = max_cols_per_sheet
        self.skip_empty_rows = skip_empty_rows

    def extract(self, source: Union[str, Path, bytes]) -> DocumentExtractionResult:
        """
        Extracts structured tables and text from all worksheets in an Excel workbook.
        """
        start_time = time.perf_counter()
        wb = self._open_workbook(source)

        try:
            worksheets = wb.worksheets
            if not worksheets:
                raise EmptyDocumentError("The Excel workbook contains no worksheets.")

            sheets_extraction: List[SheetExtraction] = []
            consolidated_text_parts: List[str] = []
            total_characters = 0
            total_words = 0
            total_data_rows = 0
            warnings: List[str] = []

            # Workbook properties
            wb_props = wb.properties
            wb_metadata: Dict[str, Any] = {
                'title': wb_props.title or '',
                'creator': wb_props.creator or '',
                'created': wb_props.created.isoformat() if wb_props.created else '',
                'modified': wb_props.modified.isoformat() if wb_props.modified else '',
                'sheet_count': len(worksheets),
                'sheet_names': [ws.title for ws in worksheets],
            }

            for sheet_idx, ws in enumerate(worksheets):
                sheet_name = ws.title or f"Sheet{sheet_idx + 1}"

                # Extract grid of values
                raw_rows: List[List[Any]] = []
                for row in ws.iter_rows(
                    max_row=self.max_rows_per_sheet,
                    max_col=self.max_cols_per_sheet,
                    values_only=True,
                ):
                    raw_rows.append(list(row))

                cleaned_rows, max_cols = self._clean_and_align_rows(raw_rows)
                non_empty_count = len(cleaned_rows)
                has_data = non_empty_count > 0

                headers: List[str] = []
                data_rows: List[List[Any]] = []
                table_md = ""

                if has_data:
                    # Treat first non-empty row as headers
                    headers = [str(cell) if cell is not None and str(cell).strip() != '' else f"Column_{i + 1}"
                               for i, cell in enumerate(cleaned_rows[0])]
                    data_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else []
                    total_data_rows += len(cleaned_rows)

                    # Build Markdown Table representation
                    table_md = self._build_markdown_table(headers, data_rows, max_cols)

                # Sheet text summary
                sheet_text_lines = [f"=== Worksheet: {sheet_name} ==="]
                if has_data:
                    sheet_text_lines.append(table_md)
                else:
                    sheet_text_lines.append("[Empty Worksheet]")

                sheet_text = "\n".join(sheet_text_lines)
                sheet_char_count = len(sheet_text)
                sheet_word_count = self.count_words(sheet_text)

                total_characters += sheet_char_count
                total_words += sheet_word_count

                sheet_obj = SheetExtraction(
                    sheet_index=sheet_idx,
                    sheet_name=sheet_name,
                    total_rows=len(raw_rows),
                    total_columns=max_cols,
                    non_empty_rows=non_empty_count,
                    headers=headers,
                    rows=cleaned_rows,
                    table_markdown=table_md,
                    character_count=sheet_char_count,
                    word_count=sheet_word_count,
                    has_data=has_data,
                )
                sheets_extraction.append(sheet_obj)
                consolidated_text_parts.append(sheet_text)

            full_consolidated_text = "\n\n".join(consolidated_text_parts)
            has_extractable_text = total_data_rows > 0

            is_scanned_or_low_text = not has_extractable_text
            low_text_reason = None
            if not has_extractable_text:
                low_text_reason = "Excel workbook contains no non-empty rows across any worksheet."
                warnings.append("Workbook is completely blank.")

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DocumentExtractionResult(
                document_type='excel',
                total_units=len(worksheets),
                raw_text=full_consolidated_text,
                character_count=total_characters,
                word_count=total_words,
                pages=[],
                sheets=sheets_extraction,
                metadata=wb_metadata,
                has_extractable_text=has_extractable_text,
                is_scanned_or_low_text=is_scanned_or_low_text,
                low_text_reason=low_text_reason,
                warnings=warnings,
                processing_time_ms=elapsed_ms,
            )

        finally:
            wb.close()

    def _format_cell_value(self, cell_value: Any) -> Any:
        """
        Formats diverse Excel cell data types into clean Python types / strings.
        """
        if cell_value is None:
            return None

        if isinstance(cell_value, datetime):
            if cell_value.hour == 0 and cell_value.minute == 0 and cell_value.second == 0:
                return cell_value.strftime('%Y-%m-%d')
            return cell_value.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(cell_value, date):
            return cell_value.isoformat()

        if isinstance(cell_value, float):
            # If float is an integer value like 10.0, format as 10
            if cell_value.is_integer():
                return int(cell_value)
            return round(cell_value, 4)

        if isinstance(cell_value, bool):
            return "TRUE" if cell_value else "FALSE"

        if isinstance(cell_value, str):
            cleaned = self.normalize_text(cell_value)
            return cleaned if cleaned else None

        return str(cell_value).strip()

    def _clean_and_align_rows(
        self, raw_rows: List[List[Any]]
    ) -> Tuple[List[List[Any]], int]:
        """
        Cleans cell values, strips trailing empty rows, and standardizes row lengths.
        """
        formatted_rows: List[List[Any]] = []
        max_col_with_data = 0

        for row in raw_rows:
            formatted_row = [self._format_cell_value(cell) for cell in row]

            # Check if row is completely empty
            has_data = any(val is not None and str(val).strip() != '' for val in formatted_row)
            if not has_data and self.skip_empty_rows:
                continue

            # Track maximum column index containing non-empty data
            for col_idx in range(len(formatted_row) - 1, -1, -1):
                if formatted_row[col_idx] is not None and str(formatted_row[col_idx]).strip() != '':
                    max_col_with_data = max(max_col_with_data, col_idx + 1)
                    break

            formatted_rows.append(formatted_row)

        if not formatted_rows or max_col_with_data == 0:
            return [], 0

        # Trim all rows to max_col_with_data for uniform tabular columns
        aligned_rows: List[List[Any]] = []
        for row in formatted_rows:
            # Slice up to max_col_with_data and pad if necessary
            sliced = row[:max_col_with_data]
            if len(sliced) < max_col_with_data:
                sliced.extend([None] * (max_col_with_data - len(sliced)))
            aligned_rows.append(sliced)

        return aligned_rows, max_col_with_data

    def _build_markdown_table(
        self, headers: List[str], data_rows: List[List[Any]], col_count: int
    ) -> str:
        """
        Builds a markdown table representation from headers and data rows.
        Escapes pipes and converts inner newlines to spaces so table structure remains valid.
        """
        if col_count == 0:
            return ""

        # Pad headers if fewer than col_count
        clean_headers = [str(h).replace('|', '\\|').replace('\n', ' ') for h in headers]
        while len(clean_headers) < col_count:
            clean_headers.append(f"Col_{len(clean_headers) + 1}")

        header_line = "| " + " | ".join(clean_headers[:col_count]) + " |"
        separator_line = "| " + " | ".join(["---"] * col_count) + " |"

        table_lines = [header_line, separator_line]

        for row in data_rows:
            row_cells: List[str] = []
            for col_idx in range(col_count):
                val = row[col_idx] if col_idx < len(row) else None
                cell_str = "" if val is None else str(val).replace('|', '\\|').replace('\n', ' ')
                row_cells.append(cell_str)
            table_lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(table_lines)

    def _open_workbook(self, source: Union[str, Path, bytes]) -> openpyxl.Workbook:
        """
        Safely loads an Excel workbook using openpyxl with data_only=True to read evaluated formula values.
        """
        try:
            if isinstance(source, (str, Path)):
                path_obj = Path(source)
                if not path_obj.exists():
                    raise FileNotFoundError(f"Excel file not found at: {source}")
                if path_obj.stat().st_size == 0:
                    raise EmptyDocumentError("Excel file is empty (0 bytes).")
                return openpyxl.load_workbook(str(path_obj), data_only=True, read_only=False)
            elif isinstance(source, bytes):
                if len(source) == 0:
                    raise EmptyDocumentError("Excel byte stream is empty (0 bytes).")
                byte_stream = io.BytesIO(source)
                return openpyxl.load_workbook(byte_stream, data_only=True, read_only=False)
            else:
                raise CorruptDocumentError(f"Unsupported source type: {type(source)}")

        except (EmptyDocumentError, FileNotFoundError):
            raise
        except InvalidFileException as ife:
            raise CorruptDocumentError(f"Invalid Excel file format: {str(ife)}") from ife
        except Exception as e:
            raise CorruptDocumentError(f"Failed to open or parse Excel workbook: {str(e)}") from e
