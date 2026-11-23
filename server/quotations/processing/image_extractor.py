"""
Image text extraction engine using Pillow and Tesseract OCR.
Supports PNG, JPG, and JPEG quotation scans and invoice photos.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image

from .base import BaseDocumentExtractor, DocumentExtractionResult, PageExtraction
from .exceptions import CorruptDocumentError, EmptyDocumentError, TesseractNotInstalledError
from .ocr_engine import OCREngine


class ImageExtractor(BaseDocumentExtractor):
    """
    Extracts text and layout coordinates from PNG, JPG, and JPEG images using Tesseract OCR.
    """

    def __init__(self, lang: str = 'eng'):
        self.lang = lang

    def extract(self, source: Union[str, Path, bytes]) -> DocumentExtractionResult:
        """
        Loads an image, extracts dimensions, performs Tesseract OCR, and returns standardized DocumentExtractionResult.
        """
        start_time = time.perf_counter()
        img, metadata = self._open_image(source)

        try:
            warnings: List[str] = []
            extracted_text = ""
            ocr_confidence: Optional[float] = None
            word_boxes: List[Dict[str, Any]] = []
            was_ocr_performed = False

            # Check if Tesseract is available
            if OCREngine.is_available():
                try:
                    extracted_text, ocr_confidence, word_boxes = OCREngine.extract_text(img, lang=self.lang)
                    was_ocr_performed = True
                except Exception as ocr_err:
                    warnings.append(f"OCR recognition error: {str(ocr_err)}")
            else:
                warnings.append(
                    "Tesseract OCR is not installed or configured on the server. "
                    "Scanned image text recognition requires Tesseract-OCR (set TESSERACT_CMD in server/.env)."
                )

            cleaned_text = self.normalize_text(extracted_text)
            char_count = len(cleaned_text)
            word_count = self.count_words(cleaned_text)
            has_text = char_count > 0

            page_header = "--- Page 1 of 1 (Scanned Image) ---"
            raw_text = f"{page_header}\n{cleaned_text}" if has_text else f"{page_header}\n[No text recognized from image]"

            is_scanned_or_low_text = not has_text
            low_text_reason: Optional[str] = None
            if not has_text:
                if not OCREngine.is_available():
                    low_text_reason = "Image document cannot be processed because Tesseract OCR is not installed on the system."
                else:
                    low_text_reason = "Tesseract OCR completed but detected no readable text characters in the image."

            # Structure page object
            page_meta = {
                'width': metadata['width'],
                'height': metadata['height'],
                'format': metadata['format'],
                'mode': metadata['mode'],
            }

            page_obj = PageExtraction(
                page_number=1,
                text=cleaned_text,
                character_count=char_count,
                word_count=word_count,
                has_text=has_text,
                extraction_method='ocr' if was_ocr_performed else 'none',
                ocr_confidence=ocr_confidence,
                blocks=word_boxes,
                metadata=page_meta,
            )

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DocumentExtractionResult(
                document_type='image',
                total_units=1,
                raw_text=raw_text,
                character_count=char_count,
                word_count=word_count,
                pages=[page_obj],
                sheets=[],
                metadata=metadata,
                has_extractable_text=has_text,
                is_scanned_or_low_text=is_scanned_or_low_text,
                low_text_reason=low_text_reason,
                was_ocr_performed=was_ocr_performed,
                ocr_pages=[1] if was_ocr_performed else [],
                ocr_confidence=ocr_confidence,
                warnings=warnings,
                processing_time_ms=elapsed_ms,
            )

        finally:
            img.close()

    def _open_image(self, source: Union[str, Path, bytes]) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Safely opens image source with Pillow and extracts basic dimension metadata.
        """
        import io

        try:
            if isinstance(source, (str, Path)):
                path_obj = Path(source)
                if not path_obj.exists():
                    raise FileNotFoundError(f"Image file not found at: {source}")
                if path_obj.stat().st_size == 0:
                    raise EmptyDocumentError("Image file is empty (0 bytes).")
                img = Image.open(str(path_obj))
            elif isinstance(source, bytes):
                if len(source) == 0:
                    raise EmptyDocumentError("Image byte stream is empty (0 bytes).")
                img = Image.open(io.BytesIO(source))
            else:
                raise CorruptDocumentError(f"Unsupported image source type: {type(source)}")

            # Verify image integrity
            img.load()
            metadata = {
                'format': img.format or 'IMAGE',
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
            }
            return img, metadata

        except (EmptyDocumentError, FileNotFoundError):
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Failed to open or parse image: {str(e)}") from e
