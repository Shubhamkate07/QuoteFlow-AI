"""
Base interfaces and standard data structures for document text extraction in QuoteFlow AI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re


@dataclass
class PageExtraction:
    """
    Structured extraction result for a single PDF page or image document.
    Tracks whether text was extracted natively or via OCR, and records OCR confidence.
    """
    page_number: int  # 1-indexed
    text: str
    character_count: int
    word_count: int
    has_text: bool
    extraction_method: str = "native_text"  # 'native_text', 'ocr', 'hybrid'
    ocr_confidence: Optional[float] = None  # 0.0 - 100.0 if OCR was performed
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SheetExtraction:
    """
    Structured extraction result for an Excel worksheet.
    """
    sheet_index: int  # 0-indexed
    sheet_name: str
    total_rows: int
    total_columns: int
    non_empty_rows: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    table_markdown: str = ""
    character_count: int = 0
    word_count: int = 0
    has_data: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentExtractionResult:
    """
    Unified extraction result standard across all document formats (PDF, Excel, Image).
    Explicitly tracks OCR invocation and confidence.
    """
    document_type: str  # 'pdf', 'excel', 'image'
    total_units: int  # total pages for PDF/image, total sheets for Excel
    raw_text: str  # full consolidated text representation
    character_count: int
    word_count: int
    pages: List[PageExtraction] = field(default_factory=list)
    sheets: List[SheetExtraction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    has_extractable_text: bool = True
    is_scanned_or_low_text: bool = False
    low_text_reason: Optional[str] = None
    was_ocr_performed: bool = False
    ocr_pages: List[int] = field(default_factory=list)
    ocr_confidence: Optional[float] = None  # average confidence percentage (0.0 to 100.0)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts extraction result into a clean dictionary suitable for JSON serialization.
        """
        return {
            'document_type': self.document_type,
            'total_units': self.total_units,
            'character_count': self.character_count,
            'word_count': self.word_count,
            'has_extractable_text': self.has_extractable_text,
            'is_scanned_or_low_text': self.is_scanned_or_low_text,
            'low_text_reason': self.low_text_reason,
            'was_ocr_performed': self.was_ocr_performed,
            'ocr_pages': self.ocr_pages,
            'ocr_confidence': round(self.ocr_confidence, 2) if self.ocr_confidence is not None else None,
            'warnings': self.warnings,
            'processing_time_ms': self.processing_time_ms,
            'metadata': self.metadata,
            'pages': [page.to_dict() for page in self.pages],
            'sheets': [sheet.to_dict() for sheet in self.sheets],
        }


class BaseDocumentExtractor(ABC):
    """
    Abstract base class for modular document extractors.
    All format-specific extractors (PDF, Excel, Image) inherit from this class.
    """

    LOW_TEXT_AVG_CHARS_PER_PAGE: int = 25
    LOW_TEXT_TOTAL_CHARS_THRESHOLD: int = 40

    @abstractmethod
    def extract(self, source: Union[str, Path, bytes]) -> DocumentExtractionResult:
        """
        Extracts structured text and metadata from the given document file or byte stream.
        """
        pass

    @staticmethod
    def count_words(text: str) -> int:
        """Counts words using whitespace splitting and stripping punctuation."""
        if not text:
            return 0
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizes unicode characters, line endings, and excessive horizontal whitespace."""
        if not text:
            return ""
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = text.replace('\xa0', ' ')
        text = text.replace('\x00', '')
        return text.strip()
