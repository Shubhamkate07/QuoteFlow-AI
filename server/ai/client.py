"""
Reusable, thread-safe Gemini AI Client for QuoteFlow AI.
Encapsulates Google GenAI SDK client creation, configuration validation,
timeout management, and secure credential handling.
"""

import os
import logging
import threading
from dataclasses import dataclass
from typing import Optional
from django.conf import settings
from google import genai
from google.genai import types

from ai.exceptions import GeminiConfigurationError
from ai.utils import mask_api_key

os.environ.setdefault('GOOGLE_GENAI_API_VERSION', 'v1beta')

logger = logging.getLogger('quoteflow.ai.client')


@dataclass
class GeminiConfig:
    """Configuration parameters for Gemini AI services."""
    api_key: str
    model_name: str = 'gemini-3.5-flash'
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    temperature: float = 0.1

    @classmethod
    def from_settings(cls) -> 'GeminiConfig':
        """Loads configuration from Django settings."""
        raw_model = getattr(settings, 'GEMINI_MODEL_NAME', 'gemini-3.5-flash').strip() or 'gemini-3.5-flash'
        if raw_model in ('gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro', 'gemini-2.5-flash-lite'):
            raw_model = 'gemini-3.5-flash'
        return cls(
            api_key=getattr(settings, 'GEMINI_API_KEY', '').strip(),
            model_name=raw_model,
            timeout_seconds=int(getattr(settings, 'GEMINI_TIMEOUT_SECONDS', 60)),
            max_retries=int(getattr(settings, 'GEMINI_MAX_RETRIES', 3)),
            retry_backoff_factor=float(getattr(settings, 'GEMINI_RETRY_BACKOFF_FACTOR', 2.0)),
            temperature=float(getattr(settings, 'GEMINI_TEMPERATURE', 0.1)),
        )

    @property
    def is_configured(self) -> bool:
        """Checks whether a non-empty API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    @property
    def masked_key(self) -> str:
        """Returns the masked API key for safe display and logging."""
        return mask_api_key(self.api_key)

    def validate(self) -> None:
        """Validates that mandatory credentials exist."""
        if not self.is_configured:
            raise GeminiConfigurationError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in your backend .env file."
            )

    def __repr__(self) -> str:
        return (
            f"<GeminiConfig model='{self.model_name}' "
            f"api_key='{self.masked_key}' "
            f"timeout={self.timeout_seconds}s "
            f"retries={self.max_retries}>"
        )


class GeminiClient:
    """
    Manages the underlying google-genai Client instance.
    Supports lazy instantiation to allow backend startup without an active key,
    while enforcing strict validation when API calls are made.
    """

    def __init__(self, config: Optional[GeminiConfig] = None):
        self._config = config or GeminiConfig.from_settings()
        self._native_client: Optional[genai.Client] = None
        self._lock = threading.Lock()

    @property
    def config(self) -> GeminiConfig:
        return self._config

    def get_client(self) -> genai.Client:
        """
        Returns an initialized genai.Client.
        Thread-safe lazy initialization.
        """
        if self._native_client is None:
            with self._lock:
                if self._native_client is None:
                    self._config.validate()
                    logger.debug(
                        "Initializing Google GenAI client with model=%s, timeout=%ds, key=%s",
                        self._config.model_name,
                        self._config.timeout_seconds,
                        self._config.masked_key,
                    )
                    http_options = types.HttpOptions(
                        timeout=self._config.timeout_seconds * 1000,
                        api_version='v1beta',
                    )
                    self._native_client = genai.Client(
                        api_key=self._config.api_key,
                        http_options=http_options,
                    )
        return self._native_client

    def reset(self) -> None:
        """Resets cached client (useful when settings/keys are updated in tests)."""
        with self._lock:
            self._native_client = None

    def __repr__(self) -> str:
        return f"<GeminiClient config={self._config!r} initialized={self._native_client is not None}>"


# Thread-safe singleton instance
_GLOBAL_CLIENT: Optional[GeminiClient] = None
_GLOBAL_LOCK = threading.Lock()


def get_gemini_client(reload: bool = False) -> GeminiClient:
    """
    Returns the application-wide GeminiClient singleton.
    Pass reload=True to force re-reading configuration from Django settings.
    """
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None or reload:
        with _GLOBAL_LOCK:
            if _GLOBAL_CLIENT is None or reload:
                _GLOBAL_CLIENT = GeminiClient(GeminiConfig.from_settings())
    return _GLOBAL_CLIENT
