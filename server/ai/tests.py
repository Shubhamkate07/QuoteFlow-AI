"""
Comprehensive automated tests for Gemini AI integration in QuoteFlow AI.
Tests client configuration, secret sanitization, retry strategy,
rate limit handling, timeout management, structured schema extraction, and API view security.
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from google.genai import errors, types
from pydantic import BaseModel, Field
from rest_framework import status
from rest_framework.test import APITestCase

from ai.client import GeminiClient, GeminiConfig, get_gemini_client
from ai.exceptions import (
    GeminiAPIError,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiContentBlockedError,
    GeminiRateLimitError,
    GeminiResponseParsingError,
    GeminiTimeoutError,
)
from ai.service import GeminiService
from ai.utils import mask_api_key, sanitize_log_message
from organizations.models import Organization, OrganizationMembership, OrganizationRole
from users.models import User


class DummyQuotationSchema(BaseModel):
    vendor: str = Field(description="Vendor name")
    part_number: str = Field(description="Part number")
    quantity: int = Field(description="Quantity")
    unit_price: float = Field(description="Unit price")


class GeminiUtilsTests(TestCase):
    """Tests utility functions for secret protection and log sanitization."""

    def test_mask_api_key(self):
        """Verifies API keys are masked properly."""
        self.assertEqual(mask_api_key(""), "[NOT CONFIGURED]")
        self.assertEqual(mask_api_key(None), "[NOT CONFIGURED]")
        self.assertEqual(mask_api_key("short"), "****")
        self.assertEqual(mask_api_key("AIzaSyD1234567890abcdefghijklmnop"), "AIza****mnop")

    def test_sanitize_log_message(self):
        """Verifies sensitive keys are stripped from log messages."""
        secret = "AIzaSyD_MyVerySecretKey1234567890_X"
        msg = f"Failed to connect using key {secret} due to network timeout."
        sanitized = sanitize_log_message(msg, secret)
        self.assertNotIn(secret, sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)


class GeminiConfigAndClientTests(TestCase):
    """Tests configuration parsing and client lifecycle."""

    def test_config_from_settings(self):
        """Tests reading configuration from Django settings."""
        with override_settings(
            GEMINI_API_KEY="AIzaSyTestKey1234567890abcdefghij",
            GEMINI_MODEL_NAME="gemini-3.5-flash",
            GEMINI_TIMEOUT_SECONDS=45,
            GEMINI_MAX_RETRIES=2,
            GEMINI_RETRY_BACKOFF_FACTOR=1.5,
            GEMINI_TEMPERATURE=0.2,
        ):
            config = GeminiConfig.from_settings()
            self.assertEqual(config.model_name, "gemini-3.5-flash")
            self.assertEqual(config.timeout_seconds, 45)
            self.assertEqual(config.max_retries, 2)
            self.assertEqual(config.retry_backoff_factor, 1.5)
            self.assertEqual(config.temperature, 0.2)
            self.assertTrue(config.is_configured)
            self.assertEqual(config.masked_key, "AIza****ghij")
            self.assertNotIn("AIzaSyTestKey", repr(config))

    def test_client_validation_missing_key_raises_error(self):
        """Tests that attempting to initialize a client without an API key raises GeminiConfigurationError."""
        config = GeminiConfig(api_key="")
        client = GeminiClient(config)
        with self.assertRaises(GeminiConfigurationError):
            client.get_client()


class GeminiServiceTests(TestCase):
    """Tests GeminiService logic, retry strategy, and error handling with mocked SDK calls."""

    def setUp(self):
        self.config = GeminiConfig(
            api_key="AIzaSyMockKeyForTesting1234567890",
            model_name="gemini-3.5-flash",
            timeout_seconds=5,
            max_retries=2,
            retry_backoff_factor=1.0,
            temperature=0.1,
        )
        self.mock_client = MagicMock()
        self.mock_native = MagicMock()
        self.mock_client.config = self.config
        self.mock_client.get_client.return_value = self.mock_native
        self.service = GeminiService(client=self.mock_client)

    def test_generate_text_success(self):
        """Tests successful freeform text generation."""
        mock_response = MagicMock()
        mock_response.text = "QuoteFlow AI is operational."
        self.mock_native.models.generate_content.return_value = mock_response

        result = self.service.generate_text("Status check?")
        self.assertEqual(result, "QuoteFlow AI is operational.")
        self.mock_native.models.generate_content.assert_called_once()

    def test_generate_text_empty_prompt_raises_value_error(self):
        """Tests that empty prompts are rejected immediately."""
        with self.assertRaises(ValueError):
            self.service.generate_text("   ")

    def test_generate_structured_pydantic_schema_success(self):
        """Tests structured output validated against a Pydantic BaseModel."""
        mock_response = MagicMock()
        mock_response.text = '{"vendor": "Apex Dynamics", "part_number": "VALVE-400", "quantity": 10, "unit_price": 85.50}'
        self.mock_native.models.generate_content.return_value = mock_response

        extracted = self.service.generate_structured(
            prompt="Extract item details",
            response_schema=DummyQuotationSchema,
        )

        self.assertIsInstance(extracted, DummyQuotationSchema)
        self.assertEqual(extracted.vendor, "Apex Dynamics")
        self.assertEqual(extracted.part_number, "VALVE-400")
        self.assertEqual(extracted.quantity, 10)
        self.assertEqual(extracted.unit_price, 85.50)

    def test_generate_structured_invalid_json_raises_parsing_error(self):
        """Tests that invalid JSON response raises GeminiResponseParsingError."""
        mock_response = MagicMock()
        mock_response.text = 'NOT VALID JSON CONTENT'
        self.mock_native.models.generate_content.return_value = mock_response

        with self.assertRaises(GeminiResponseParsingError):
            self.service.generate_structured(
                prompt="Extract item details",
                response_schema=DummyQuotationSchema,
            )

    @patch('time.sleep', return_value=None)
    def test_rate_limit_retry_strategy(self, mock_sleep):
        """Tests automatic retry with backoff when HTTP 429 is encountered."""
        # First call fails with 429, second call succeeds
        mock_429 = errors.APIError(429, "Resource has been exhausted (check quota).")
        mock_success = MagicMock()
        mock_success.text = "Succeeded after rate limit retry."

        self.mock_native.models.generate_content.side_effect = [mock_429, mock_success]

        result = self.service.generate_text("Test prompt")
        self.assertEqual(result, "Succeeded after rate limit retry.")
        self.assertEqual(self.mock_native.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once()

    @patch('time.sleep', return_value=None)
    def test_transient_503_error_retried(self, mock_sleep):
        """Tests automatic retry when Google returns transient 503 Service Unavailable."""
        mock_503 = errors.APIError(503, "The model is currently overloaded. Please try again.")
        mock_success = MagicMock()
        mock_success.text = "Succeeded after 503."

        self.mock_native.models.generate_content.side_effect = [mock_503, mock_success]

        result = self.service.generate_text("Test prompt")
        self.assertEqual(result, "Succeeded after 503.")
        self.assertEqual(self.mock_native.models.generate_content.call_count, 2)

    def test_authentication_error_fails_immediately_without_retry(self):
        """Tests that HTTP 401/403 fails fast without wasting retries."""
        mock_403 = errors.APIError(403, "API_KEY_INVALID: Your API key is not valid.")
        self.mock_native.models.generate_content.side_effect = mock_403

        with self.assertRaises(GeminiAuthenticationError):
            self.service.generate_text("Test prompt")

        # Must not retry authentication failures
        self.assertEqual(self.mock_native.models.generate_content.call_count, 1)

    def test_timeout_handling(self):
        """Tests that timeouts are caught and mapped to GeminiTimeoutError."""
        self.mock_native.models.generate_content.side_effect = Exception("The read operation timed out")

        with self.assertRaises(GeminiTimeoutError):
            self.service.generate_text("Test prompt")

    def test_count_tokens(self):
        """Tests token counting delegation."""
        mock_count_resp = MagicMock()
        mock_count_resp.total_tokens = 42
        self.mock_native.models.count_tokens.return_value = mock_count_resp

        tokens = self.service.count_tokens("Calculate token length for this string")
        self.assertEqual(tokens, 42)

    def test_health_check_healthy(self):
        """Tests health_check returns healthy status when API responds."""
        mock_response = MagicMock()
        mock_response.text = "Pong"
        self.mock_native.models.generate_content.return_value = mock_response

        status_dict = self.service.health_check()
        self.assertEqual(status_dict['status'], 'healthy')
        self.assertTrue(status_dict['configured'])
        self.assertEqual(status_dict['model'], 'gemini-3.5-flash')
        self.assertIn("AIza****7890", status_dict['masked_key'])
        self.assertNotIn("AIzaSyMockKeyForTesting", str(status_dict))

    def test_health_check_unconfigured(self):
        """Tests health_check returns unconfigured status when API key is empty."""
        unconfigured_client = GeminiClient(GeminiConfig(api_key=""))
        unconfigured_service = GeminiService(client=unconfigured_client)

        status_dict = unconfigured_service.health_check()
        self.assertEqual(status_dict['status'], 'unconfigured')
        self.assertFalse(status_dict['configured'])


class AIHealthCheckAPITests(APITestCase):
    """Tests the GET /api/ai/health/ endpoint and ensures API keys are never exposed."""

    def setUp(self):
        self.org = Organization.objects.create(name="Health Org", slug="health-org")
        self.user = User.objects.create_user(
            email="aiadmin@healthorg.com",
            password="SecurePassword123!",
            first_name="AI",
            last_name="Admin",
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationRole.ADMIN,
        )

    def test_health_endpoint_requires_authentication(self):
        """Tests that unauthenticated requests to /api/ai/health/ are rejected with 401."""
        response = self.client.get("/api/ai/health/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_health_endpoint_authenticated(self):
        """Tests that authenticated requests succeed and NEVER leak the raw API key."""
        self.client.force_authenticate(user=self.user)

        with patch.object(GeminiService, 'health_check') as mock_health:
            mock_health.return_value = {
                'status': 'healthy',
                'configured': True,
                'model': 'gemini-3.5-flash',
                'masked_key': 'AIza****9999',
                'latency_ms': 120.5,
            }
            response = self.client.get("/api/ai/health/")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'healthy')
            self.assertEqual(response.data['masked_key'], 'AIza****9999')
            # Verify raw key is not anywhere in the response payload
            self.assertNotIn("AIzaSy", str(response.data))
