"""
Pydantic v2 schemas for AI-powered quotation extraction in QuoteFlow AI.
Enforces strict typing, evidence tracking, missing field nullability,
and structured outputs compatible with Gemini's response_schema parameter.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


def _coerce_optional_float(val: Any) -> Optional[float]:
    """
    Coerces raw string, numeric, or European-formatted values into a clean float.
    Handles currency symbols ($1,250.00), accounting negatives ('(800.00)', '-$800.00'),
    European decimal commas ('13,75', '1.425,50'), and empty / placeholder values ('', 'N/A', '-').
    """
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if not s or s.lower() in ("none", "null", "n/a", "-", "nan", "nil"):
            return None
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            s = s[1:-1].strip()
        elif s.startswith("-"):
            is_negative = True
            s = s[1:].strip()
        elif s.endswith("-"):
            is_negative = True
            s = s[:-1].strip()

        # Remove currency symbols and whitespace
        s = re.sub(r'[\$€£₹¥\s]', '', s)
        if not s:
            return None
        # Handle decimal commas vs dots
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                # European notation: 1.425,50 -> 1425.50
                s = s.replace('.', '').replace(',', '.')
            else:
                # US/UK notation: 1,425.50 -> 1425.50
                s = s.replace(',', '')
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        try:
            num = float(s)
            return -num if is_negative else num
        except (ValueError, TypeError):
            return None
    return None


class FieldEvidence(BaseModel):
    """
    Evidence tracing for an extracted commercial value back to the source text.
    Ensures accountability and provenance for human auditing.
    """
    extracted_value: Optional[str] = Field(
        default=None,
        description="The value as extracted from the document",
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Verbatim exact snippet of text from the source document where this was found",
    )
    page_number: Optional[int] = Field(
        default=None,
        description="1-based page number where the evidence appears",
    )
    confidence_level: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for this specific field between 0.0 (low) and 1.0 (certain)",
    )


class SpecificationItem(BaseModel):
    """Key-value technical or dimension specification for a line item."""
    name: str = Field(description="Specification parameter name (e.g. Material, Voltage, Size, Tolerance)")
    value: str = Field(description="Specification value (e.g. 316 Stainless Steel, 24V DC, 8mm x 40mm)")


class SupplierInfoSchema(BaseModel):
    """Supplier vendor details extracted from header/contact block."""
    supplier_name: Optional[str] = Field(default=None, description="Legal company name or trade name of the supplier")
    contact_person: Optional[str] = Field(default=None, description="Sales rep, account manager, or contact name")
    email: Optional[str] = Field(default=None, description="Supplier contact email address")
    phone: Optional[str] = Field(default=None, description="Supplier telephone or fax number")
    address: Optional[str] = Field(default=None, description="Supplier physical or mailing address")
    quotation_number: Optional[str] = Field(default=None, description="Quotation reference number or proposal ID")


class QuotationInfoSchema(BaseModel):
    """Quotation commercial header metadata and high-level financial totals."""
    quotation_date: Optional[str] = Field(default=None, description="Quotation issuance date in YYYY-MM-DD format if identifiable, else verbatim string")
    validity_date: Optional[str] = Field(default=None, description="Quotation expiration / validity date in YYYY-MM-DD format if identifiable, else verbatim string")
    currency: Optional[str] = Field(default=None, description="3-letter ISO currency code (USD, EUR, GBP, INR, JPY, CAD, etc.)")
    subtotal: Optional[float] = Field(default=None, description="Net subtotal before tax and shipping stated on the document (numeric only)")
    tax: Optional[float] = Field(default=None, description="Total tax, VAT, or GST amount stated on the document (numeric only)")
    discount: Optional[float] = Field(default=None, description="Document-level or overall discount stated on the document (numeric only)")
    shipping: Optional[float] = Field(default=None, description="Shipping, freight, or handling fees stated on the document (numeric only)")
    grand_total: Optional[float] = Field(default=None, description="Final payable grand total stated on the document (numeric only)")

    @field_validator('subtotal', 'tax', 'discount', 'shipping', 'grand_total', mode='before')
    @classmethod
    def coerce_currency_float(cls, v: Any) -> Optional[float]:
        return _coerce_optional_float(v)


class LineItemSchema(BaseModel):
    """Individual line item or bill of materials entry quoted by the supplier."""
    line_number: Optional[int] = Field(default=None, description="1-based sequence or item number from the quotation table")
    description: str = Field(description="Full product or service item description as stated")
    manufacturer: Optional[str] = Field(default=None, description="Brand or manufacturer name if explicitly stated")
    model: Optional[str] = Field(default=None, description="Model number, SKU, MPN, or part number")
    quantity: Optional[float] = Field(default=None, description="Quantity quoted (numeric)")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. PCS, EA, KG, M, BOX, SET)")
    unit_price: Optional[float] = Field(default=None, description="Price per individual unit before line discount (numeric)")
    discount: Optional[float] = Field(default=None, description="Line item discount amount (numeric)")
    tax: Optional[float] = Field(default=None, description="Line item tax amount if itemized (numeric)")
    total: Optional[float] = Field(default=None, description="Total extended price for this line item (numeric)")
    specifications: List[SpecificationItem] = Field(default_factory=list, description="Extracted technical specifications")
    source_text: Optional[str] = Field(default=None, description="Verbatim line text from document")
    page_number: Optional[int] = Field(default=None, description="Page number where this line item is located")
    confidence_level: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Extraction confidence score for this item")

    @field_validator('quantity', 'unit_price', 'discount', 'tax', 'total', mode='before')
    @classmethod
    def coerce_numeric_float(cls, v: Any) -> Optional[float]:
        return _coerce_optional_float(v)


class CommercialTermsSchema(BaseModel):
    """Contractual, delivery, payment, and warranty terms."""
    delivery_time: Optional[str] = Field(default=None, description="Lead time or delivery timeframe (e.g. '3-4 weeks ARO', 'Immediate from stock')")
    delivery_terms: Optional[str] = Field(default=None, description="Incoterms or shipping terms (e.g. FOB Chicago, EXW Frankfurt, DDP Dallas, CIF Mumbai)")
    payment_terms: Optional[str] = Field(default=None, description="Commercial payment terms (e.g. Net 30, Net 60, 50% advance / 50% prior to dispatch)")
    warranty: Optional[str] = Field(default=None, description="Warranty duration and terms (e.g. '12 months from delivery', '2 years manufacturer warranty')")
    notes: Optional[str] = Field(default=None, description="Supplier special conditions, price validity caveats, or notes")


class EvidenceCollectionSchema(BaseModel):
    """Evidence citations connecting key header fields back to their source document locations."""
    supplier_name: Optional[FieldEvidence] = None
    quotation_number: Optional[FieldEvidence] = None
    quotation_date: Optional[FieldEvidence] = None
    validity_date: Optional[FieldEvidence] = None
    currency: Optional[FieldEvidence] = None
    subtotal: Optional[FieldEvidence] = None
    tax: Optional[FieldEvidence] = None
    shipping: Optional[FieldEvidence] = None
    grand_total: Optional[FieldEvidence] = None
    delivery_terms: Optional[FieldEvidence] = None
    payment_terms: Optional[FieldEvidence] = None
    warranty: Optional[FieldEvidence] = None


class QuotationExtractionSchema(BaseModel):
    """
    Root extraction schema consumed by Gemini AI.
    Guarantees structured, strongly-typed JSON output conforming to procurement requirements.
    """
    supplier: SupplierInfoSchema = Field(description="Extracted supplier company and contact details")
    quotation: QuotationInfoSchema = Field(description="Extracted quotation metadata and financial totals")
    line_items: List[LineItemSchema] = Field(default_factory=list, description="Extracted line items from tables and lists")
    commercial_terms: CommercialTermsSchema = Field(description="Extracted commercial, shipping, payment, and warranty conditions")
    evidence: EvidenceCollectionSchema = Field(default_factory=EvidenceCollectionSchema, description="Audit evidence citations with page numbers")
    overall_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Overall document extraction confidence score")
    summary: Optional[str] = Field(default=None, description="Brief 1-2 sentence procurement summary of this quotation")
