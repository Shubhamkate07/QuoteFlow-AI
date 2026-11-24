"""
Gemini AI Service for QuoteFlow AI.
Provides resilient text and structured JSON generation, automatic retry strategies
with exponential backoff, rate limit handling, timeout protection,
and secret-safe logging.
"""

import json
import logging
import random
import time
from typing import Any, Dict, Optional, Type, Union
from google.genai import errors, types
from pydantic import BaseModel

from ai.client import GeminiClient, get_gemini_client
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
from ai.utils import mask_api_key, sanitize_log_message

logger = logging.getLogger('quoteflow.ai.service')


class GeminiService:
    """
    High-level, production-grade Gemini service for QuoteFlow AI.
    Features:
    - Robust error translation from SDK exceptions to domain exceptions
    - Configurable retry strategy with exponential backoff and jitter
    - Rate limit (HTTP 429) backoff with Retry-After header parsing
    - Structured JSON output generation via response_mime_type and Pydantic schemas
    - Sanitized logging preventing credential exposure
    - Latency tracking and health check diagnostics
    """

    def __init__(self, client: Optional[GeminiClient] = None):
        self._client = client or get_gemini_client()

    @property
    def client(self) -> GeminiClient:
        return self._client

    @property
    def config(self):
        return self._client.config

    def _map_exception(self, exc: Exception) -> GeminiError:
        """Translates low-level SDK and HTTP errors into typed domain exceptions."""
        if isinstance(exc, GeminiError):
            return exc

        err_str = str(exc)
        api_key = self.config.api_key

        # 1. Google GenAI APIError inspection
        if isinstance(exc, errors.APIError):
            code = getattr(exc, 'code', None)
            sanitized_msg = sanitize_log_message(err_str, api_key)

            if code in (401, 403) or "API_KEY_INVALID" in err_str or "PERMISSION_DENIED" in err_str:
                return GeminiAuthenticationError(
                    f"Authentication failed: {sanitized_msg}",
                    status_code=code or 401,
                )
            if code == 429 or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                return GeminiRateLimitError(
                    f"Rate limit exceeded: {sanitized_msg}",
                    status_code=429,
                )
            if code in (500, 502, 503, 504):
                return GeminiAPIError(
                    f"Upstream Google service error: {sanitized_msg}",
                    status_code=code,
                    retryable=True,
                )
            return GeminiAPIError(
                f"Gemini API error: {sanitized_msg}",
                status_code=code,
                retryable=False,
            )

        # 2. Timeout errors
        if "timeout" in err_str.lower() or "timed out" in err_str.lower():
            return GeminiTimeoutError(
                f"Request exceeded timeout of {self.config.timeout_seconds}s: {sanitize_log_message(err_str, api_key)}",
                timeout_seconds=self.config.timeout_seconds,
            )

        # 3. Connection and generic network errors
        sanitized_msg = sanitize_log_message(err_str, api_key)
        return GeminiAPIError(f"Unexpected error communicating with Gemini: {sanitized_msg}", status_code=500, retryable=True)

    def _execute_with_retry(self, operation, operation_name: str = "GenerateContent") -> Any:
        """
        Executes a Gemini SDK call with exponential backoff and jitter on retryable failures.
        """
        max_retries = self.config.max_retries
        backoff_factor = self.config.retry_backoff_factor
        last_error: Optional[GeminiError] = None

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                result = operation()
                elapsed_ms = (time.time() - start_time) * 1000
                logger.debug(
                    "Gemini %s succeeded on attempt %d/%d (%.2f ms)",
                    operation_name,
                    attempt + 1,
                    max_retries + 1,
                    elapsed_ms,
                )
                return result

            except Exception as raw_exc:
                mapped_err = self._map_exception(raw_exc)
                last_error = mapped_err

                # Non-retryable errors fail immediately
                if not mapped_err.retryable or attempt >= max_retries:
                    sanitized_err = sanitize_log_message(str(mapped_err), self.config.api_key)
                    logger.error(
                        "Gemini %s failed (non-retryable or retries exhausted): %s",
                        operation_name,
                        sanitized_err,
                    )
                    raise mapped_err from raw_exc

                # Calculate backoff delay with jitter
                base_delay = 1.0 * (backoff_factor ** attempt)
                jitter = random.uniform(0.1, 0.5)
                delay = base_delay + jitter

                if isinstance(mapped_err, GeminiRateLimitError) and mapped_err.retry_after:
                    delay = max(delay, mapped_err.retry_after)

                sanitized_msg = sanitize_log_message(mapped_err.message, self.config.api_key)
                logger.warning(
                    "Gemini %s failed (attempt %d/%d): %s. Retrying in %.2fs...",
                    operation_name,
                    attempt + 1,
                    max_retries + 1,
                    sanitized_msg,
                    delay,
                )
                time.sleep(delay)

        if last_error:
            raise last_error

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Generates freeform text using the configured Gemini model.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        target_model = model or self.config.model_name
        if target_model in ('gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro', 'gemini-2.5-flash-lite'):
            target_model = 'gemini-3.5-flash'
        gen_temp = temperature if temperature is not None else self.config.temperature

        config = types.GenerateContentConfig(
            temperature=gen_temp,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
        )

        candidate_models = [target_model]
        for fallback in ['gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.8-flash']:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        response = None
        last_call_err = None
        for current_model in candidate_models:
            def _call():
                native = self.client.get_client()
                return native.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=config,
                )

            try:
                response = self._execute_with_retry(_call, operation_name=f"TextGeneration[{current_model}]")
                break
            except Exception as call_err:
                logger.warning("Model %s failed (%s), trying next fallback model...", current_model, call_err)
                last_call_err = call_err
                continue

        if response is None:
            if last_call_err:
                raise last_call_err
            raise GeminiAPIError("Failed to obtain response from any candidate Gemini model.", status_code=500)

        # Validate response content
        if not response or not response.text:
            # Check for safety filter blocks
            candidates = getattr(response, 'candidates', [])
            if candidates and getattr(candidates[0], 'finish_reason', None) == 'SAFETY':
                raise GeminiContentBlockedError("Response was blocked by Gemini safety filters.")
            return ""

        return response.text

    def generate_structured(
        self,
        prompt: str,
        response_schema: Union[Type[BaseModel], Dict[str, Any]],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> Union[Dict[str, Any], BaseModel]:
        """
        Generates strictly conforming structured JSON output using Gemini's native
        JSON schema mode (response_mime_type="application/json").

        Accepts either a Pydantic BaseModel class or a raw JSON schema dictionary.
        Returns a validated instance of the Pydantic model or a parsed Python dictionary.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        target_model = model or self.config.model_name
        if target_model in ('gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro', 'gemini-2.5-flash-lite'):
            target_model = 'gemini-3.5-flash'
        gen_temp = temperature if temperature is not None else self.config.temperature

        # Build schema configuration
        is_pydantic = isinstance(response_schema, type) and issubclass(response_schema, BaseModel)

        config = types.GenerateContentConfig(
            temperature=gen_temp,
            response_mime_type="application/json",
            response_schema=response_schema,
            system_instruction=system_instruction,
        )

        candidate_models = [target_model]
        for fallback in ['gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.8-flash']:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        response = None
        last_call_err = None
        for current_model in candidate_models:
            def _call():
                native = self.client.get_client()
                return native.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=config,
                )

            try:
                response = self._execute_with_retry(_call, operation_name=f"StructuredGeneration[{current_model}]")
                break
            except Exception as call_err:
                logger.warning("Model %s failed (%s), trying next fallback model...", current_model, call_err)
                last_call_err = call_err
                continue

        if response is None:
            if last_call_err:
                raise last_call_err
            raise GeminiAPIError("Failed to obtain response from any candidate Gemini model.", status_code=500)

        raw_text = getattr(response, 'text', '') or ''
        if not raw_text.strip():
            raise GeminiResponseParsingError("Gemini returned an empty response body.", raw_response=raw_text)

        # Parse JSON
        try:
            parsed_json = json.loads(raw_text)
        except json.JSONDecodeError as decode_err:
            logger.error("Failed to decode JSON from Gemini: %s. Raw: %s", decode_err, raw_text[:200])
            raise GeminiResponseParsingError(
                f"Failed to parse Gemini output as JSON: {decode_err}",
                raw_response=raw_text,
            ) from decode_err

        # Validate with Pydantic if class provided
        if is_pydantic:
            try:
                return response_schema.model_validate(parsed_json)
            except Exception as val_err:
                logger.error("Pydantic validation failed for Gemini JSON output: %s", val_err)
                raise GeminiResponseParsingError(
                    f"Generated JSON does not match schema: {val_err}",
                    raw_response=raw_text,
                ) from val_err

        return parsed_json

    def count_tokens(self, contents: str, model: Optional[str] = None) -> int:
        """
        Calculates token count for input contents using Gemini's tokenizer.
        """
        target_model = model or self.config.model_name
        try:
            native = self.client.get_client()
            response = native.models.count_tokens(
                model=target_model,
                contents=contents,
            )
            return getattr(response, 'total_tokens', 0)
        except Exception as e:
            logger.warning("Token counting failed: %s", sanitize_log_message(str(e), self.config.api_key))
            # Fallback estimation: ~4 chars per token
            return max(1, len(contents) // 4)

    def health_check(self) -> Dict[str, Any]:
        """
        Performs a lightweight validation of backend Gemini connectivity and credentials.
        Returns a health status dictionary without exposing any API keys.
        """
        if not self.config.is_configured:
            return {
                'status': 'unconfigured',
                'configured': False,
                'model': self.config.model_name,
                'masked_key': '[NOT SET]',
                'message': 'GEMINI_API_KEY is not configured in backend environment.',
            }

        start_time = time.time()
        try:
            # Simple 1-word generation to verify network, auth, and model availability
            response = self.generate_text(
                prompt="Ping",
                max_output_tokens=5,
                temperature=0.0,
            )
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                'status': 'healthy',
                'configured': True,
                'model': self.config.model_name,
                'masked_key': self.config.masked_key,
                'latency_ms': latency_ms,
                'timeout_seconds': self.config.timeout_seconds,
                'max_retries': self.config.max_retries,
            }
        except GeminiError as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                'status': 'unhealthy',
                'configured': True,
                'model': self.config.model_name,
                'masked_key': self.config.masked_key,
                'latency_ms': latency_ms,
                'error_type': e.__class__.__name__,
                'error_message': sanitize_log_message(e.message, self.config.api_key),
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                'status': 'error',
                'configured': True,
                'model': self.config.model_name,
                'masked_key': self.config.masked_key,
                'latency_ms': latency_ms,
                'error_type': e.__class__.__name__,
                'error_message': sanitize_log_message(str(e), self.config.api_key),
            }
