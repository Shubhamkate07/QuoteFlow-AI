"""
PDF text extraction engine using PyMuPDF (fitz) with automatic OCR fallback.
Supports multi-page text extraction, page-by-page tracking, block parsing,
scanned document detection, and Tesseract OCR rendering for scanned pages.
"""

import io
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from .base import BaseDocumentExtractor, DocumentExtractionResult, PageExtraction
from .exceptions import (
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedDocumentError,
)
from .ocr_engine import OCREngine


class PDFExtractor(BaseDocumentExtractor):
    """
    Extracts text, structured layout blocks, and metadata from PDF files using PyMuPDF.
    Automatically detects scanned / low-text PDFs and renders pages into images for Tesseract OCR.
    """

    def __init__(
        self,
        min_total_chars_threshold: int = BaseDocumentExtractor.LOW_TEXT_TOTAL_CHARS_THRESHOLD,
        min_avg_chars_per_page: int = BaseDocumentExtractor.LOW_TEXT_AVG_CHARS_PER_PAGE,
        extract_blocks: bool = True,
        enable_ocr: bool = True,
        ocr_dpi: int = 200,
    ):
        self.min_total_chars_threshold = min_total_chars_threshold
        self.min_avg_chars_per_page = min_avg_chars_per_page
        self.extract_blocks = extract_blocks
        self.enable_ocr = enable_ocr
        self.ocr_dpi = ocr_dpi

    def extract(self, source: Union[str, Path, bytes]) -> DocumentExtractionResult:
        """
        Extracts page-by-page text, layout blocks, detects scanned/low-text PDFs,
        and renders relevant pages to images for OCR if needed.
        """
        start_time = time.perf_counter()
        doc = self._open_document(source)

        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise EmptyDocumentError("The PDF document contains 0 pages.")

            # Document metadata
            doc_metadata: Dict[str, Any] = {
                'format': doc.metadata.get('format', 'PDF'),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'creator': doc.metadata.get('creator', ''),
                'producer': doc.metadata.get('producer', ''),
                'creation_date': doc.metadata.get('creationDate', ''),
                'mod_date': doc.metadata.get('modDate', ''),
                'page_count': total_pages,
                'is_encrypted': doc.is_encrypted,
            }

            pages_extraction: List[PageExtraction] = []
            total_characters = 0
            total_words = 0
            warnings: List[str] = []

            # 1. First pass: native PyMuPDF text and block extraction
            for page_index in range(total_pages):
                page_number = page_index + 1
                page = doc[page_index]

                raw_page_text = page.get_text("text", sort=True) or ""
                cleaned_page_text = self.normalize_text(raw_page_text)
                char_count = len(cleaned_page_text)
                word_count = self.count_words(cleaned_page_text)
                has_text = char_count > 0

                if has_text:
                    total_characters += char_count
                    total_words += word_count

                blocks_data: List[Dict[str, Any]] = []
                if self.extract_blocks and has_text:
                    try:
                        raw_blocks = page.get_text("blocks", sort=True)
                        for b in raw_blocks:
                            if len(b) >= 7 and b[6] == 0:  # text block
                                block_text = self.normalize_text(b[4])
                                if block_text:
                                    blocks_data.append({
                                        'bbox': [round(coord, 2) for coord in b[:4]],
                                        'text': block_text,
                                        'block_number': b[5],
                                    })
                    except Exception as block_err:
                        warnings.append(f"Page {page_number}: Block extraction failed ({str(block_err)}).")

                page_rect = page.rect
                page_meta = {
                    'width': round(page_rect.width, 2),
                    'height': round(page_rect.height, 2),
                    'rotation': page.rotation,
                    'has_images': len(page.get_images()) > 0,
                    'image_count': len(page.get_images()),
                }

                page_obj = PageExtraction(
                    page_number=page_number,
                    text=cleaned_page_text,
                    character_count=char_count,
                    word_count=word_count,
                    has_text=has_text,
                    extraction_method='native_text',
                    ocr_confidence=None,
                    blocks=blocks_data,
                    tables=[],
                    metadata=page_meta,
                )
                pages_extraction.append(page_obj)

            # 2. Scanned / Low-Text PDF Detection
            avg_chars_per_page = (total_characters / total_pages) if total_pages > 0 else 0
            is_scanned_or_low_text = (
                total_characters < self.min_total_chars_threshold
                or avg_chars_per_page < self.min_avg_chars_per_page
            )

            was_ocr_performed = False
            ocr_pages: List[int] = []
            ocr_confidences: List[float] = []

            # 3. Second pass: Fallback to OCR for low-text or scanned pages
            if is_scanned_or_low_text and self.enable_ocr:
                if OCREngine.is_available():
                    for page_index in range(total_pages):
                        page_obj = pages_extraction[page_index]
                        # Target pages with no text or very low text density
                        if page_obj.character_count < self.min_avg_chars_per_page:
                            page_number = page_index + 1
                            page = doc[page_index]
                            try:
                                # Render page to image at high resolution (200 DPI)
                                pix = page.get_pixmap(dpi=self.ocr_dpi)
                                img_bytes = pix.tobytes("png")
                                with Image.open(io.BytesIO(img_bytes)) as pil_img:
                                    ocr_text, ocr_conf, ocr_blocks = OCREngine.extract_text(pil_img)

                                cleaned_ocr_text = self.normalize_text(ocr_text)
                                if cleaned_ocr_text and len(cleaned_ocr_text) > page_obj.character_count:
                                    had_native_text = page_obj.has_text and page_obj.character_count > 0
                                    page_obj.text = cleaned_ocr_text
                                    page_obj.character_count = len(cleaned_ocr_text)
                                    page_obj.word_count = self.count_words(cleaned_ocr_text)
                                    page_obj.has_text = True
                                    page_obj.extraction_method = 'hybrid' if had_native_text else 'ocr'
                                    page_obj.ocr_confidence = ocr_conf
                                    page_obj.blocks = ocr_blocks or page_obj.blocks

                                    was_ocr_performed = True
                                    ocr_pages.append(page_number)
                                    if ocr_conf is not None:
                                        ocr_confidences.append(ocr_conf)

                            except Exception as ocr_page_err:
                                warnings.append(f"Page {page_number}: OCR failed ({str(ocr_page_err)}).")

                    # Recompute totals after OCR
                    total_characters = sum(p.character_count for p in pages_extraction)
                    total_words = sum(p.word_count for p in pages_extraction)
                    avg_chars_per_page = total_characters / total_pages

                    if total_characters >= self.min_total_chars_threshold:
                        is_scanned_or_low_text = False

                else:
                    warnings.append(
                        "Document contains little or no digital text and appears scanned, "
                        "but Tesseract OCR is not installed or configured on the server."
                    )

            # 4. Final text consolidation and metrics
            consolidated_text_parts: List[str] = []
            for p in pages_extraction:
                method_tag = " (OCR Extracted)" if p.extraction_method == 'ocr' else ""
                header = f"--- Page {p.page_number} of {total_pages}{method_tag} ---"
                if p.text:
                    consolidated_text_parts.append(f"{header}\n{p.text}")
                else:
                    consolidated_text_parts.append(f"{header}\n[No extractable digital text on page]")

            full_consolidated_text = "\n\n".join(consolidated_text_parts)
            has_extractable_text = total_characters > 0

            low_text_reason: Optional[str] = None
            if is_scanned_or_low_text:
                low_text_reason = (
                    f"Document contains only {total_characters} characters across {total_pages} page(s) "
                    f"(average {avg_chars_per_page:.1f} chars/page, threshold {self.min_avg_chars_per_page}). "
                    f"This document appears to be a scanned image or photo without an embedded digital text layer."
                )
                if not any("Low text density" in w for w in warnings):
                    warnings.append("Low text density: Scanned or image-based PDF detected.")

            overall_ocr_confidence: Optional[float] = None
            if ocr_confidences:
                overall_ocr_confidence = round(sum(ocr_confidences) / len(ocr_confidences), 2)

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DocumentExtractionResult(
                document_type='pdf',
                total_units=total_pages,
                raw_text=full_consolidated_text,
                character_count=total_characters,
                word_count=total_words,
                pages=pages_extraction,
                sheets=[],
                metadata=doc_metadata,
                has_extractable_text=has_extractable_text,
                is_scanned_or_low_text=is_scanned_or_low_text,
                low_text_reason=low_text_reason,
                was_ocr_performed=was_ocr_performed,
                ocr_pages=ocr_pages,
                ocr_confidence=overall_ocr_confidence,
                warnings=warnings,
                processing_time_ms=elapsed_ms,
            )

        finally:
            doc.close()

    def _open_document(self, source: Union[str, Path, bytes]) -> fitz.Document:
        """
        Safely opens a PDF document from a filepath or byte stream, verifying encryption.
        """
        try:
            if isinstance(source, (str, Path)):
                path_obj = Path(source)
                if not path_obj.exists():
                    raise FileNotFoundError(f"PDF file not found at: {source}")
                if path_obj.stat().st_size == 0:
                    raise EmptyDocumentError("PDF file is empty (0 bytes).")
                doc = fitz.open(str(path_obj))
            elif isinstance(source, bytes):
                if len(source) == 0:
                    raise EmptyDocumentError("PDF byte stream is empty (0 bytes).")
                doc = fitz.open(stream=source, filetype="pdf")
            else:
                raise CorruptDocumentError(f"Unsupported source type: {type(source)}")

            if doc.is_encrypted:
                if not doc.authenticate(""):
                    doc.close()
                    raise EncryptedDocumentError("The PDF document is password-protected or encrypted.")

            return doc

        except (EmptyDocumentError, EncryptedDocumentError, FileNotFoundError):
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Failed to open or parse PDF document: {str(e)}") from e
