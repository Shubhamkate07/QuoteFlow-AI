"""
Master Quotation Normalization Service.
Deterministic coordinator that normalizes raw/extracted quotations before multi-supplier comparison:
1. Normalizes Currencies and executes explicit currency conversion only when valid rate citations exist.
2. Normalizes Units of Measure (UOM) ensuring mathematical invariance (Quantity * Unit Price).
3. Reconciles Taxes (Percent vs Fixed amounts, Inclusive vs Exclusive).
4. Reconciles Discounts (Percent vs Lump-sum).
5. Standardizes Delivery Timelines (Days vs Weeks vs Months vs Ex-stock).
6. Standardizes Payment Terms (Advance % vs Credit Days vs Risk scoring).
7. Standardizes Warranty Coverage (Months vs Days vs Types).
"""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union

from .currency import (
    CurrencyConversionService,
    ExchangeRateTable,
    MissingExchangeRateError,
    normalize_currency_code,
)
from .lead_time import normalize_lead_time
from .payment_terms import normalize_payment_terms
from .warranty import normalize_warranty
from .schemas import (
    NormalizedCommercialTerms,
    NormalizedFinancials,
    NormalizedLineItem,
    NormalizedQuotation,
)
from .tax_and_discount import normalize_discount, normalize_tax
from .uom import canonicalize_uom, convert_quantity_and_price


class QuotationNormalizationService:
    """
    Production-grade deterministic normalization service.
    Can be called directly with:
    - Raw dictionary extracted from document (QuotationExtraction.extracted_data)
    - Django Quotation model instance
    """

    def __init__(self, exchange_rate_table: Optional[ExchangeRateTable] = None):
        self.rate_table = exchange_rate_table or ExchangeRateTable()
        self.currency_service = CurrencyConversionService(self.rate_table)

    def normalize(
        self,
        extracted_data: Dict[str, Any],
        target_currency: Optional[str] = None,
        target_rfq_items: Optional[List[Dict[str, Any]]] = None,
        conversion_date: Optional[date] = None,
        quotation_id: Optional[str] = None,
        extraction_id: Optional[str] = None,
        rfq_id: Optional[str] = None,
    ) -> NormalizedQuotation:
        """
        Normalizes a quotation data bundle deterministically.
        """
        notes: List[str] = []
        warnings: List[str] = []

        supplier_dict = extracted_data.get('supplier', {}) or {}
        quote_dict = extracted_data.get('quotation', {}) or {}
        terms_dict = extracted_data.get('commercial_terms', {}) or {}
        raw_items = extracted_data.get('line_items', []) or []

        supplier_name = supplier_dict.get('supplier_name') or extracted_data.get('supplier_name') or 'Unknown Supplier'
        quotation_number = supplier_dict.get('quotation_number') or extracted_data.get('quotation_number') or 'N/A'

        quote_date = self._parse_date(quote_dict.get('quotation_date') or extracted_data.get('quotation_date'))
        validity_date = self._parse_date(quote_dict.get('validity_date') or extracted_data.get('validity_date'))

        # ---------------- 1. Currency Setup ----------------
        raw_curr = quote_dict.get('currency') or extracted_data.get('currency') or 'USD'
        native_currency = normalize_currency_code(raw_curr)
        resolved_target_curr = normalize_currency_code(target_currency) if target_currency else native_currency

        can_convert_currency = False
        rate_entry = None
        if resolved_target_curr != native_currency:
            rate_entry = self.rate_table.get_rate(native_currency, resolved_target_curr, as_of_date=conversion_date)
            if rate_entry:
                can_convert_currency = True
                notes.append(
                    f"Converted currency from {native_currency} to {resolved_target_curr} at rate {rate_entry.rate} "
                    f"(Source: {rate_entry.rate_source}, Date: {rate_entry.rate_date})."
                )
            else:
                warnings.append(
                    f"Currency conversion to {resolved_target_curr} skipped: No explicit exchange rate found for {native_currency}->{resolved_target_curr}. "
                    f"Exchange rates are never invented. Retaining native currency {native_currency}."
                )
                resolved_target_curr = native_currency

        # ---------------- 2. Commercial Terms ----------------
        norm_lead_time = normalize_lead_time(
            terms_dict.get('delivery_time') or extracted_data.get('delivery_time')
        )
        norm_payment_terms = normalize_payment_terms(
            terms_dict.get('payment_terms') or extracted_data.get('payment_terms')
        )
        norm_warranty = normalize_warranty(
            terms_dict.get('warranty') or extracted_data.get('warranty')
        )
        delivery_terms = str(terms_dict.get('delivery_terms') or extracted_data.get('delivery_terms') or '').strip()
        commercial_notes = str(terms_dict.get('notes') or extracted_data.get('notes') or '').strip()

        norm_commercial_terms = NormalizedCommercialTerms(
            lead_time=norm_lead_time,
            payment_terms=norm_payment_terms,
            warranty=norm_warranty,
            delivery_terms=delivery_terms,
            notes=commercial_notes,
        )

        # ---------------- 3. Line Items Normalization ----------------
        normalized_items: List[NormalizedLineItem] = []
        calc_native_subtotal = Decimal('0.00')
        calc_norm_subtotal = Decimal('0.00')

        rfq_target_map: Dict[str, str] = {}
        if target_rfq_items:
            for item in target_rfq_items:
                if 'id' in item and 'unit' in item:
                    rfq_target_map[str(item['id'])] = item['unit']

        for idx, item in enumerate(raw_items):
            line_no = item.get('line_number') or (idx + 1)
            desc = item.get('description') or f"Line Item #{line_no}"
            mfr = item.get('manufacturer') or ''
            model = item.get('model') or ''

            native_qty = Decimal(str(item.get('quantity') or '1.0'))
            native_unit = item.get('unit') or 'PCS'
            native_price = Decimal(str(item.get('unit_price') or '0.00'))
            native_disc = Decimal(str(item.get('discount') or '0.00'))
            native_tax = Decimal(str(item.get('tax') or '0.00'))
            native_total = Decimal(str(item.get('total') or ((native_qty * native_price) - native_disc + native_tax)))

            rfq_item_id = item.get('rfq_item_id')
            target_unit = rfq_target_map.get(str(rfq_item_id)) if rfq_item_id else None

            # UOM Normalization (Quantity & Unit Price invariant scaling)
            norm_qty, norm_price, norm_unit, factor, is_uom_converted = convert_quantity_and_price(
                native_qty, native_price, native_unit, target_unit=target_unit
            )

            _, uom_category = canonicalize_uom(norm_unit)

            if is_uom_converted:
                notes.append(
                    f"Line #{line_no}: Normalized UOM from {native_qty} {native_unit} to {norm_qty} {norm_unit} "
                    f"(Unit price adjusted from {native_price} to {norm_price} / {norm_unit})."
                )

            # Currency Conversion for Line Item (if active)
            item_conv_rec = None
            if can_convert_currency:
                price_conv = self.currency_service.convert(
                    norm_price, native_currency, resolved_target_curr, as_of_date=conversion_date
                )
                norm_price = price_conv.converted_amount
                item_conv_rec = price_conv

                disc_conv = self.currency_service.convert(
                    native_disc, native_currency, resolved_target_curr, as_of_date=conversion_date
                )
                norm_disc = disc_conv.converted_amount

                tax_conv = self.currency_service.convert(
                    native_tax, native_currency, resolved_target_curr, as_of_date=conversion_date
                )
                norm_tax = tax_conv.converted_amount

                norm_total = ((norm_qty * norm_price) - norm_disc + norm_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                norm_disc = native_disc
                norm_tax = native_tax
                norm_total = ((norm_qty * norm_price) - norm_disc + norm_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            calc_native_subtotal += (native_qty * native_price) - native_disc
            calc_norm_subtotal += (norm_qty * norm_price) - norm_disc

            norm_line = NormalizedLineItem(
                line_number=line_no,
                description=desc,
                manufacturer=mfr,
                model=model,
                native_quantity=native_qty,
                native_unit=native_unit,
                native_unit_price=native_price,
                native_discount=native_disc,
                native_tax=native_tax,
                native_total=native_total,
                normalized_quantity=norm_qty,
                normalized_unit=norm_unit,
                normalized_unit_price=norm_price,
                normalized_total=norm_total,
                uom_conversion_factor=factor,
                uom_category=uom_category.value,
                specifications=item.get('specifications', []),
                rfq_item_id=rfq_item_id,
                match_type=item.get('match_type', 'exact'),
                currency_conversion=item_conv_rec,
            )
            normalized_items.append(norm_line)

        # ---------------- 4. Tax & Discount Normalization ----------------
        stated_native_subtotal = Decimal(str(quote_dict.get('subtotal') or calc_native_subtotal))
        stated_native_tax = Decimal(str(quote_dict.get('tax') or '0.00'))
        stated_native_disc = Decimal(str(quote_dict.get('discount') or '0.00'))
        stated_native_ship = Decimal(str(quote_dict.get('shipping') or '0.00'))

        tax_norm = normalize_tax(
            subtotal=stated_native_subtotal,
            stated_tax_amount=stated_native_tax if stated_native_tax > Decimal('0.0') else None,
            tax_name_or_clause=terms_dict.get('notes'),
        )

        disc_norm = normalize_discount(
            gross_amount=stated_native_subtotal,
            stated_discount_amount=stated_native_disc if stated_native_disc > Decimal('0.0') else None,
        )

        effective_tax = tax_norm.tax_amount
        effective_disc = disc_norm.discount_amount
        native_grand_total = (stated_native_subtotal + effective_tax + stated_native_ship - effective_disc).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # ---------------- 5. Financial Conversion ----------------
        fin_conv_rec = None
        if can_convert_currency:
            subtotal_conv = self.currency_service.convert(stated_native_subtotal, native_currency, resolved_target_curr, conversion_date)
            tax_conv = self.currency_service.convert(effective_tax, native_currency, resolved_target_curr, conversion_date)
            disc_conv = self.currency_service.convert(effective_disc, native_currency, resolved_target_curr, conversion_date)
            ship_conv = self.currency_service.convert(stated_native_ship, native_currency, resolved_target_curr, conversion_date)
            total_conv = self.currency_service.convert(native_grand_total, native_currency, resolved_target_curr, conversion_date)

            norm_financials = NormalizedFinancials(
                native_currency=native_currency,
                normalized_currency=resolved_target_curr,
                native_subtotal=stated_native_subtotal,
                native_tax=effective_tax,
                native_discount=effective_disc,
                native_shipping=stated_native_ship,
                native_grand_total=native_grand_total,
                normalized_subtotal=subtotal_conv.converted_amount,
                normalized_tax=tax_conv.converted_amount,
                normalized_discount=disc_conv.converted_amount,
                normalized_shipping=ship_conv.converted_amount,
                normalized_grand_total=total_conv.converted_amount,
                tax_details=tax_norm,
                discount_details=disc_norm,
                currency_conversion=total_conv,
            )
        else:
            norm_financials = NormalizedFinancials(
                native_currency=native_currency,
                normalized_currency=native_currency,
                native_subtotal=stated_native_subtotal,
                native_tax=effective_tax,
                native_discount=effective_disc,
                native_shipping=stated_native_ship,
                native_grand_total=native_grand_total,
                normalized_subtotal=stated_native_subtotal,
                normalized_tax=effective_tax,
                normalized_discount=effective_disc,
                normalized_shipping=stated_native_ship,
                normalized_grand_total=native_grand_total,
                tax_details=tax_norm,
                discount_details=disc_norm,
                currency_conversion=None,
            )

        return NormalizedQuotation(
            supplier_name=supplier_name,
            quotation_number=quotation_number,
            quotation_date=quote_date,
            validity_date=validity_date,
            financials=norm_financials,
            commercial_terms=norm_commercial_terms,
            items=normalized_items,
            quotation_id=quotation_id,
            extraction_id=extraction_id,
            rfq_id=rfq_id,
            normalization_notes=notes,
            warnings=warnings,
        )

    def normalize_quotation_model(
        self,
        quotation,
        target_currency: Optional[str] = None,
        conversion_date: Optional[date] = None,
    ) -> NormalizedQuotation:
        """
        Convenience method to normalize a Django Quotation model instance.
        """
        items_payload = []
        for it in quotation.items.all():
            items_payload.append({
                'line_number': it.position,
                'description': it.description,
                'manufacturer': it.manufacturer,
                'model': it.model,
                'quantity': float(it.quantity),
                'unit': it.unit,
                'unit_price': float(it.unit_price),
                'discount': float(it.discount),
                'tax': float(it.tax),
                'total': float((it.quantity * it.unit_price) - it.discount + it.tax),
                'rfq_item_id': str(it.rfq_item_id) if it.rfq_item_id else None,
                'match_type': it.match_type,
            })

        # Derive shipping if grand total exceeds subtotal + tax
        derived_shipping = max(Decimal('0.00'), quotation.total_amount - quotation.subtotal - quotation.tax_amount)

        payload = {
            'supplier': {
                'supplier_name': quotation.supplier.company_name if quotation.supplier_id else 'Unknown Supplier',
                'quotation_number': quotation.quotation_number,
            },
            'quotation': {
                'quotation_date': quotation.quotation_date.isoformat() if quotation.quotation_date else None,
                'validity_date': quotation.validity_date.isoformat() if quotation.validity_date else None,
                'currency': quotation.currency,
                'subtotal': float(quotation.subtotal),
                'tax': float(quotation.tax_amount),
                'shipping': float(derived_shipping),
                'grand_total': float(quotation.total_amount),
            },
            'commercial_terms': {
                'delivery_time': f"{quotation.lead_time_weeks} weeks" if quotation.lead_time_weeks else '',
                'delivery_terms': quotation.delivery_terms,
                'payment_terms': quotation.payment_terms,
                'warranty': quotation.warranty_information,
                'notes': quotation.notes,
            },
            'line_items': items_payload,
        }

        rfq_items = []
        if quotation.rfq_id:
            for ritem in quotation.rfq.items.all():
                rfq_items.append({'id': str(ritem.id), 'unit': ritem.unit})

        return self.normalize(
            extracted_data=payload,
            target_currency=target_currency or quotation.rfq.currency if quotation.rfq_id else None,
            target_rfq_items=rfq_items,
            conversion_date=conversion_date,
            quotation_id=str(quotation.id),
            rfq_id=str(quotation.rfq_id) if quotation.rfq_id else None,
        )

    def _parse_date(self, val: Any) -> Optional[date]:
        if not val:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        try:
            return date.fromisoformat(str(val).strip()[:10])
        except Exception:
            return None
