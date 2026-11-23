"""
Tesseract OCR Engine for QuoteFlow AI.
Encapsulates Tesseract binary auto-discovery, image preprocessing with Pillow,
text recognition, and OCR confidence metric calculation.
"""

import io
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageEnhance, ImageOps
import pytesseract
from pytesseract import TesseractNotFoundError

from .exceptions import OCRError, TesseractNotInstalledError


class OCREngine:
    """
    Modular wrapper around pytesseract and Pillow for extracting text from scanned pages and images.
    """

    _tesseract_path: Optional[str] = None
    _is_checked: bool = False
    _is_available: bool = False

    @classmethod
    def find_tesseract_binary(cls) -> Optional[str]:
        """
        Auto-detects the tesseract binary across environment variables, PATH,
        and standard Windows / Linux / macOS installation directories.
        """
        if cls._is_checked:
            return cls._tesseract_path

        cls._is_checked = True

        # 1. Check explicit environment variable
        env_cmd = os.environ.get('TESSERACT_CMD')
        if env_cmd and os.path.exists(env_cmd):
            cls._tesseract_path = env_cmd
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            cls._is_available = True
            return cls._tesseract_path

        # 2. Check system PATH
        path_binary = shutil.which('tesseract')
        if path_binary:
            cls._tesseract_path = path_binary
            cls._is_available = True
            return cls._tesseract_path

        # 3. Check standard Windows installation directories
        windows_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in windows_candidates:
            if os.path.exists(candidate):
                cls._tesseract_path = candidate
                pytesseract.pytesseract.tesseract_cmd = candidate
                cls._is_available = True
                return cls._tesseract_path

        # 4. Check standard Unix paths
        unix_candidates = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ]
        for candidate in unix_candidates:
            if os.path.exists(candidate):
                cls._tesseract_path = candidate
                pytesseract.pytesseract.tesseract_cmd = candidate
                cls._is_available = True
                return cls._tesseract_path

        cls._is_available = False
        return None

    @classmethod
    def is_available(cls) -> bool:
        """
        Returns True if Tesseract OCR binary is installed and executable.
        """
        binary = cls.find_tesseract_binary()
        if not binary:
            return False
        try:
            # Test invocation
            pytesseract.get_tesseract_version()
            cls._is_available = True
            return True
        except Exception:
            cls._is_available = False
            return False

    @classmethod
    def preprocess_image(cls, img: Image.Image) -> Image.Image:
        """
        Preprocesses a PIL Image to optimize OCR recognition accuracy:
        - Converts RGBA/transparency to RGB with white background
        - Converts to high-contrast grayscale
        - Applies moderate auto-contrast
        """
        # 1. Remove alpha channel / transparency if present
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 2. Convert to grayscale for OCR thresholding
        grayscale = ImageOps.grayscale(img)

        # 3. Normalize histogram & stretch contrast (eliminates gray background wash)
        autocontrasted = ImageOps.autocontrast(grayscale, cutoff=2)

        # 4. Enhance contrast to sharpen character boundaries
        enhancer = ImageEnhance.Contrast(autocontrasted)
        enhanced = enhancer.enhance(1.5)

        # 5. Adaptive point thresholding to eliminate background scanner grain
        table = [0 if i < 195 else 255 for i in range(256)]
        binarized = enhanced.point(table, 'L')

        return binarized

    @classmethod
    def extract_text(
        cls,
        image_input: Union[Image.Image, bytes, str, Path],
        lang: str = 'eng',
    ) -> Tuple[str, Optional[float], List[Dict[str, Any]]]:
        """
        Performs OCR on an image and returns:
        - Cleaned text string
        - Average word confidence percentage (0.0 to 100.0)
        - List of word boxes with bounding coordinates and individual confidence scores

        :raises TesseractNotInstalledError: If Tesseract OCR binary is not found.
        :raises OCRError: If OCR processing fails.
        """
        if not cls.is_available():
            raise TesseractNotInstalledError(
                "Tesseract OCR is not installed or tesseract.exe was not found. "
                "Please install Tesseract-OCR on your system or set TESSERACT_CMD in server/.env."
            )

        # Load image if input is bytes or path
        img = None
        should_close = False
        try:
            if isinstance(image_input, Image.Image):
                img = image_input
            elif isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input))
                should_close = True
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input))
                should_close = True
            else:
                raise OCRError(f"Unsupported image input type: {type(image_input)}")

            processed_img = cls.preprocess_image(img)

            # 1. Extract plain text
            text = pytesseract.image_to_string(processed_img, lang=lang) or ""
            cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n').strip()

            # 2. Extract layout and word confidence metrics
            word_boxes: List[Dict[str, Any]] = []
            confidence_sum = 0.0
            valid_words_count = 0

            try:
                data = pytesseract.image_to_data(
                    processed_img,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                )
                n_boxes = len(data.get('text', []))
                for i in range(n_boxes):
                    word = (data['text'][i] or '').strip()
                    conf_val = float(data['conf'][i])
                    if conf_val >= 0 and word:
                        confidence_sum += conf_val
                        valid_words_count += 1
                        word_boxes.append({
                            'text': word,
                            'confidence': round(conf_val, 2),
                            'bbox': [
                                data['left'][i],
                                data['top'][i],
                                data['width'][i],
                                data['height'][i],
                            ],
                        })
            except Exception:
                # If word data fails, still preserve extracted text
                pass

            avg_confidence: Optional[float] = None
            if valid_words_count > 0:
                avg_confidence = round(confidence_sum / valid_words_count, 2)

            return cleaned_text, avg_confidence, word_boxes

        except TesseractNotFoundError as tnfe:
            raise TesseractNotInstalledError(str(tnfe)) from tnfe
        except Exception as e:
            if isinstance(e, (TesseractNotInstalledError, OCRError)):
                raise
            raise OCRError(f"Tesseract OCR failed to process image: {str(e)}") from e
        finally:
            if should_close and img:
                img.close()
