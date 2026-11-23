"""
Document Processing Exceptions for QuoteFlow AI.
"""


class DocumentProcessingError(Exception):
    """Base exception for all document processing and text extraction errors."""
    pass


class UnsupportedDocumentFormatError(DocumentProcessingError):
    """Raised when an unsupported file format or extension is provided."""
    pass


class CorruptDocumentError(DocumentProcessingError):
    """Raised when a document cannot be opened or parsed due to corruption."""
    pass


class EncryptedDocumentError(DocumentProcessingError):
    """Raised when a password-protected or encrypted document cannot be decrypted."""
    pass


class EmptyDocumentError(DocumentProcessingError):
    """Raised when an uploaded document file is completely empty (0 bytes)."""
    pass


class TesseractNotInstalledError(DocumentProcessingError):
    """Raised when OCR is requested but Tesseract-OCR binary is not found on the system."""
    pass


class OCRError(DocumentProcessingError):
    """Raised when Tesseract OCR fails during image processing."""
    pass
