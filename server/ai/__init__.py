"""
QuoteFlow AI - Artificial Intelligence Module.
Provides modular integrations with Google Gemini models for structured document extraction,
commercial intelligence, and multimodal document processing.
"""

from ai.client import GeminiClient, GeminiConfig, get_gemini_client
from ai.exceptions import (
    GeminiAPIError,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiContentBlockedError,
    GeminiError,
    GeminiRateLimitError,
    GeminiResponseParsingError,
    GeminiTimeoutError,
)
from ai.service import GeminiService
from ai.utils import mask_api_key, sanitize_log_message

__all__ = [
    'GeminiService',
    'GeminiClient',
    'GeminiConfig',
    'get_gemini_client',
    'mask_api_key',
    'sanitize_log_message',
    'GeminiError',
    'GeminiConfigurationError',
    'GeminiAuthenticationError',
    'GeminiRateLimitError',
    'GeminiTimeoutError',
    'GeminiAPIError',
    'GeminiContentBlockedError',
    'GeminiResponseParsingError',
]
