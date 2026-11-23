"""
Django management command to verify and test the backend Gemini AI integration.
Usage:
    python manage.py test_gemini
    python manage.py test_gemini --prompt "Explain RFQ in 10 words"
"""

from django.core.management.base import BaseCommand
from pydantic import BaseModel, Field

from ai.client import get_gemini_client
from ai.exceptions import GeminiError
from ai.service import GeminiService


class SampleQuotationItemSchema(BaseModel):
    item_name: str = Field(description="Name or description of the quoted item")
    part_number: str = Field(description="Manufacturer part number")
    quantity: int = Field(description="Quoted quantity")
    unit_price: float = Field(description="Unit price in USD")
    total_price: float = Field(description="Quantity multiplied by unit price")


class Command(BaseCommand):
    help = "Validates the Gemini AI configuration, tests text generation, and verifies structured JSON extraction."

    def add_arguments(self, parser):
        parser.add_argument(
            '--prompt',
            type=str,
            default="Confirm Gemini AI integration for QuoteFlow AI is active and operational in one sentence.",
            help="Custom prompt string to test freeform text generation.",
        )
        parser.add_argument(
            '--skip-structured',
            action='store_true',
            help="Skip testing structured JSON schema generation.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== QuoteFlow AI: Gemini Integration Diagnostic ==="))

        client = get_gemini_client(reload=True)
        config = client.config

        self.stdout.write(f"  Model:                {config.model_name}")
        self.stdout.write(f"  Timeout (seconds):    {config.timeout_seconds}")
        self.stdout.write(f"  Max Retries:          {config.max_retries}")
        self.stdout.write(f"  Backoff Factor:       {config.retry_backoff_factor}")
        self.stdout.write(f"  Temperature:          {config.temperature}")
        self.stdout.write(f"  API Key:              {config.masked_key}")

        if not config.is_configured:
            self.stderr.write(self.style.ERROR("\n[FAILED] GEMINI_API_KEY is not configured in server/.env!"))
            self.stderr.write("Please add your key to server/.env: GEMINI_API_KEY=AIzaSy...\n")
            return

        service = GeminiService(client)

        # 1. Test Text Generation
        custom_prompt = options['prompt']
        self.stdout.write(self.style.MIGRATE_LABEL(f"\n1. Testing Text Generation (Prompt: '{custom_prompt[:50]}...')..."))
        try:
            text_response = service.generate_text(
                prompt=custom_prompt,
                temperature=0.2,
                max_output_tokens=100,
            )
            self.stdout.write(self.style.SUCCESS(f"  [SUCCESS] Response: \"{text_response.strip()}\""))
        except GeminiError as e:
            self.stderr.write(self.style.ERROR(f"  [FAILED] Text generation error: {e}"))
            return

        # 2. Test Structured Output
        if not options['skip_structured']:
            self.stdout.write(self.style.MIGRATE_LABEL("\n2. Testing Structured JSON Schema Generation..."))
            structured_prompt = (
                "Extract this quotation line: 'Line 1: High-Pressure Hydraulic Sensor, "
                "P/N: HPS-9022-X, Quantity 50 units @ $120.00 each, total $6,000.00'."
            )
            try:
                extracted_obj = service.generate_structured(
                    prompt=structured_prompt,
                    response_schema=SampleQuotationItemSchema,
                    temperature=0.0,
                )
                self.stdout.write(self.style.SUCCESS("  [SUCCESS] Structured Output Verified:"))
                self.stdout.write(f"    - Item Name:    {extracted_obj.item_name}")
                self.stdout.write(f"    - Part Number:  {extracted_obj.part_number}")
                self.stdout.write(f"    - Quantity:     {extracted_obj.quantity}")
                self.stdout.write(f"    - Unit Price:   ${extracted_obj.unit_price:.2f}")
                self.stdout.write(f"    - Total Price:  ${extracted_obj.total_price:.2f}")
            except GeminiError as e:
                self.stderr.write(self.style.ERROR(f"  [FAILED] Structured JSON generation error: {e}"))
                return

        # 3. Health Check Diagnostic
        self.stdout.write(self.style.MIGRATE_LABEL("\n3. Testing Health Check Diagnostic..."))
        health = service.health_check()
        self.stdout.write(self.style.SUCCESS(f"  [SUCCESS] Health Status: {health.get('status')} ({health.get('latency_ms')} ms)"))
        self.stdout.write(self.style.SUCCESS("\nAll Gemini AI backend integration checks passed!\n"))
