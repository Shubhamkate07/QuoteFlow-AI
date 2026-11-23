"""
Custom exception hierarchy for Gemini AI integrations in QuoteFlow AI.
Provides clean, typed exception mapping from Google GenAI SDK errors to application-level exceptions.
"""

from typing import Optional


class GeminiError(Exception):
    """Base exception for all Gemini AI service errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable

    def __str__(self):
        code_str = f" [HTTP {self.status_code}]" if self.status_code else ""
        retry_str = " (Retryable)" if self.retryable else ""
        return f"{self.message}{code_str}{retry_str}"


class GeminiConfigurationError(GeminiError):
    """Raised when GEMINI_API_KEY is missing, empty, or improperly configured."""
    def __init__(self, message: str = "Gemini API key is not configured on the backend."):
        super().__init__(message, status_code=500, retryable=False)


class GeminiAuthenticationError(GeminiError):
    """Raised on HTTP 401 Unauthorized or 403 Forbidden (e.g. invalid or disabled API key)."""
    def __init__(self, message: str = "Invalid or unauthorized Gemini API key.", status_code: int = 401):
        super().__init__(message, status_code=status_code, retryable=False)


class GeminiRateLimitError(GeminiError):
    """Raised on HTTP 429 Too Many Requests or ResourceExhausted (rate limit or TPM/RPM quota reached)."""
    def __init__(self, message: str = "Gemini API rate limit or quota exceeded. Please retry shortly.", status_code: int = 429, retry_after: Optional[float] = None):
        super().__init__(message, status_code=status_code, retryable=True)
        self.retry_after = retry_after


class GeminiTimeoutError(GeminiError):
    """Raised when a request to the Gemini API exceeds the configured timeout threshold."""
    def __init__(self, message: str = "Gemini API request timed out.", timeout_seconds: Optional[int] = None):
        super().__init__(message, status_code=504, retryable=True)
        self.timeout_seconds = timeout_seconds


class GeminiAPIError(GeminiError):
    """Raised on unexpected upstream Google Gemini API errors (e.g. 500, 502, 503 Service Unavailable)."""
    def __init__(self, message: str, status_code: Optional[int] = 500, retryable: bool = False):
        super().__init__(message, status_code=status_code, retryable=retryable)


class GeminiContentBlockedError(GeminiError):
    """Raised when the prompt or response was blocked by Gemini safety or content filters."""
    def __init__(self, message: str = "Content generation blocked by Gemini safety filters.", block_reason: Optional[str] = None):
        super().__init__(message, status_code=400, retryable=False)
        self.block_reason = block_reason


class GeminiResponseParsingError(GeminiError):
    """Raised when structured JSON generation cannot be parsed into the expected schema."""
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message, status_code=422, retryable=False)
        self.raw_response = raw_response
