"""
Document Processing Orchestrator and Factory Service for QuoteFlow AI.
Coordinates PDF (PyMuPDF) and Excel (openpyxl) text extractors,
and manages storage of extraction results in the database.
"""

import os
from pathlib import Path
from typing import Optional, Union

from .base import BaseDocumentExtractor, DocumentExtractionResult
from .excel_extractor import ExcelExtractor
from .exceptions import (
    CorruptDocumentError,
    DocumentProcessingError,
    EmptyDocumentError,
    UnsupportedDocumentFormatError,
)
from .image_extractor import ImageExtractor
from .pdf_extractor import PDFExtractor


class DocumentProcessingService:
    """
    Central orchestration service for extracting structured text and tabular data from documents.
    """

    @classmethod
    def get_extractor(
        cls, file_type_or_extension: str, **kwargs
    ) -> BaseDocumentExtractor:
        """
        Factory method returning the appropriate extractor for the given file type or extension.
        """
        fmt = (file_type_or_extension or '').strip().lower().lstrip('.')

        if fmt in ('pdf',):
            return PDFExtractor(**kwargs)
        elif fmt in ('excel', 'xlsx', 'xls'):
            return ExcelExtractor(**kwargs)
        elif fmt in ('image', 'png', 'jpg', 'jpeg'):
            return ImageExtractor(**kwargs)
        else:
            raise UnsupportedDocumentFormatError(
                f"Unsupported document format: '{fmt}'. Supported formats are: PDF, Excel (XLSX), Image (PNG/JPG)."
            )

    @classmethod
    def extract_from_file(
        cls,
        file_path: Union[str, Path],
        file_type: Optional[str] = None,
        **kwargs,
    ) -> DocumentExtractionResult:
        """
        Extracts structured text from a local file path.
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document file not found at: {file_path}")

        fmt = file_type or path_obj.suffix.lower().lstrip('.')
        extractor = cls.get_extractor(fmt, **kwargs)
        return extractor.extract(path_obj)

    @classmethod
    def extract_from_bytes(
        cls,
        file_bytes: bytes,
        file_type: str,
        **kwargs,
    ) -> DocumentExtractionResult:
        """
        Extracts structured text from raw in-memory bytes.
        """
        extractor = cls.get_extractor(file_type, **kwargs)
        return extractor.extract(file_bytes)

    @classmethod
    def process_quotation_document(
        cls,
        document,
        save: bool = True,
        **kwargs,
    ) -> DocumentExtractionResult:
        """
        Processes a QuotationDocument model instance from the database:
        1. Validates physical file existence.
        2. Sets processing_status to 'processing'.
        3. Extracts text using PyMuPDF (PDF) or openpyxl (Excel).
        4. Stores the extraction result in the DocumentExtractionResult database model.
        5. Updates quotation document status to 'completed' with 100% progress.
        """
        # Late import to prevent circular dependencies
        from quotations.models import DocumentProcessingStatus, DocumentExtractionResult as DBMigrationResult

        if not document.file or not document.file.name:
            raise EmptyDocumentError(f"QuotationDocument #{document.id} does not have an attached file.")

        file_path = document.file.path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Underlying document file not found at: {file_path}")

        # Step 1: Mark as processing
        document.processing_status = DocumentProcessingStatus.PROCESSING
        document.processing_progress = 20
        document.processing_error = ""
        document.save(update_fields=['processing_status', 'processing_progress', 'processing_error', 'updated_at'])

        try:
            # Step 2: Determine extractor
            file_format = document.file_type or document.file_extension
            extractor = cls.get_extractor(file_format, **kwargs)

            document.processing_progress = 50
            document.save(update_fields=['processing_progress', 'updated_at'])

            # Step 3: Run extraction
            result = extractor.extract(file_path)

            document.processing_progress = 85
            document.save(update_fields=['processing_progress', 'updated_at'])

            # Step 4: Persist extraction result into the database
            if save:
                # Check for existing extraction result or create new
                DBMigrationResult.objects.update_or_create(
                    document=document,
                    defaults={
                        'organization': document.organization,
                        'document_type': result.document_type,
                        'raw_text': result.raw_text,
                        'pages_or_sheets_count': result.total_units,
                        'character_count': result.character_count,
                        'word_count': result.word_count,
                        'structured_content': result.to_dict(),
                        'metadata': result.metadata,
                        'has_extractable_text': result.has_extractable_text,
                        'is_scanned_or_low_text': result.is_scanned_or_low_text,
                        'low_text_reason': result.low_text_reason or "",
                        'was_ocr_performed': result.was_ocr_performed,
                        'ocr_confidence': result.ocr_confidence,
                        'extraction_warnings': result.warnings,
                        'processing_time_ms': int(result.processing_time_ms),
                    }
                )

            # Step 5: Mark document completed
            document.processing_status = DocumentProcessingStatus.COMPLETED
            document.processing_progress = 100
            document.processing_error = ""
            document.save(update_fields=['processing_status', 'processing_progress', 'processing_error', 'updated_at'])

            return result

        except Exception as err:
            document.processing_status = DocumentProcessingStatus.FAILED
            document.processing_progress = 0
            document.processing_error = str(err)
            document.save(update_fields=['processing_status', 'processing_progress', 'processing_error', 'updated_at'])
            raise
