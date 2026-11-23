"""
Services (business logic & write operations) for Quotations and Line Items.
All state changes and multi-table operations execute within atomic transactions.
"""

from decimal import Decimal
import os
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from rfqs.models import RFQ, RFQItem
from suppliers.models import Supplier
from quotations.models import (
    Quotation,
    QuotationItem,
    QuotationDocument,
    QuotationStatus,
    ItemMatchType,
    DocumentProcessingStatus,
)
from quotations.validators import validate_quotation_document_file


@transaction.atomic
def create_quotation(
    *,
    organization,
    user,
    rfq_id: str,
    supplier_id: str,
    quotation_number: str,
    quotation_date=None,
    validity_date=None,
    currency: str = "USD",
    status: str = QuotationStatus.RECEIVED,
    delivery_terms: str = "",
    payment_terms: str = "",
    warranty_information: str = "",
    lead_time_weeks: Decimal = None,
    notes: str = "",
    document=None,
    items: list = None,
) -> Quotation:
    """
    Creates a commercial quotation for an RFQ from an approved Supplier.
    Validates cross-tenant boundaries: both the RFQ and Supplier must belong to the organization.
    """
    # 1. Tenant boundary validation for RFQ
    rfq = RFQ.objects.filter(pk=rfq_id, organization=organization).first()
    if not rfq:
        raise ValidationError({"rfq": ["The specified RFQ does not exist in your organization."]})

    # 2. Tenant boundary validation for Supplier
    supplier = Supplier.objects.filter(pk=supplier_id, organization=organization).first()
    if not supplier:
        raise ValidationError({"supplier": ["The specified Supplier does not exist in your organization."]})

    # 3. Clean and check quotation_number
    quotation_number = str(quotation_number).strip()
    if not quotation_number:
        raise ValidationError({"quotation_number": ["Quotation number cannot be blank."]})

    if Quotation.objects.filter(
        organization=organization,
        rfq=rfq,
        supplier=supplier,
        quotation_number=quotation_number,
    ).exists():
        raise ValidationError({
            "quotation_number": [
                f'Quotation "{quotation_number}" already exists for this RFQ and Supplier in your organization.'
            ]
        })

    # 4. Date order validation
    if quotation_date and validity_date and validity_date < quotation_date:
        raise ValidationError({"validity_date": ["Validity date cannot be earlier than quotation date."]})

    quotation = Quotation(
        organization=organization,
        rfq=rfq,
        supplier=supplier,
        quotation_number=quotation_number,
        quotation_date=quotation_date,
        validity_date=validity_date,
        currency=currency.strip().upper() if currency else "USD",
        status=status,
        delivery_terms=delivery_terms.strip() if delivery_terms else "",
        payment_terms=payment_terms.strip() if payment_terms else "",
        warranty_information=warranty_information.strip() if warranty_information else "",
        lead_time_weeks=lead_time_weeks,
        notes=notes.strip() if notes else "",
        document=document,
        created_by=user,
    )
    quotation.full_clean()
    quotation.save()

    # 5. Insert initial line items if provided
    if items:
        for idx, item_data in enumerate(items, start=1):
            create_quotation_item(
                quotation=quotation,
                position=item_data.get('position', idx),
                rfq_item_id=item_data.get('rfq_item_id'),
                match_type=item_data.get('match_type', ItemMatchType.EXACT),
                description=item_data.get('description', ''),
                manufacturer=item_data.get('manufacturer', ''),
                model=item_data.get('model', ''),
                quantity=item_data.get('quantity'),
                unit=item_data.get('unit', 'PCS'),
                unit_price=item_data.get('unit_price'),
                discount=item_data.get('discount', Decimal('0.00')),
                tax=item_data.get('tax', Decimal('0.00')),
                specifications=item_data.get('specifications', {}),
                lead_time_days=item_data.get('lead_time_days'),
                notes=item_data.get('notes', ''),
                recalculate=False,
            )
        quotation.recalculate_totals(save=True)

    return quotation


@transaction.atomic
def update_quotation(
    *,
    quotation: Quotation,
    **fields,
) -> Quotation:
    """
    Updates quotation metadata, commercial terms, or status.
    Guarantees cross-tenant boundary integrity if foreign keys are updated.
    """
    organization = quotation.organization

    if 'rfq_id' in fields and fields['rfq_id']:
        rfq = RFQ.objects.filter(pk=fields['rfq_id'], organization=organization).first()
        if not rfq:
            raise ValidationError({"rfq": ["The specified RFQ does not exist in your organization."]})
        quotation.rfq = rfq

    if 'supplier_id' in fields and fields['supplier_id']:
        supplier = Supplier.objects.filter(pk=fields['supplier_id'], organization=organization).first()
        if not supplier:
            raise ValidationError({"supplier": ["The specified Supplier does not exist in your organization."]})
        quotation.supplier = supplier

    if 'quotation_number' in fields:
        new_num = str(fields['quotation_number']).strip()
        if not new_num:
            raise ValidationError({"quotation_number": ["Quotation number cannot be blank."]})
        if Quotation.objects.filter(
            organization=organization,
            rfq=quotation.rfq,
            supplier=quotation.supplier,
            quotation_number=new_num,
        ).exclude(pk=quotation.pk).exists():
            raise ValidationError({
                "quotation_number": [f'Quotation "{new_num}" already exists for this RFQ and Supplier.']
            })
        quotation.quotation_number = new_num

    for attr in [
        'quotation_date',
        'validity_date',
        'currency',
        'status',
        'delivery_terms',
        'payment_terms',
        'warranty_information',
        'lead_time_weeks',
        'notes',
        'document',
    ]:
        if attr in fields:
            setattr(quotation, attr, fields[attr])

    quotation.full_clean()
    quotation.save()
    return quotation


@transaction.atomic
def delete_quotation(*, quotation: Quotation) -> None:
    """
    Deletes a quotation and cascades to its line items.
    """
    quotation.delete()


@transaction.atomic
def create_quotation_item(
    *,
    quotation: Quotation,
    description: str,
    quantity: Decimal,
    unit_price: Decimal,
    rfq_item_id: str = None,
    match_type: str = ItemMatchType.EXACT,
    position: int = None,
    manufacturer: str = "",
    model: str = "",
    unit: str = "PCS",
    discount: Decimal = Decimal('0.00'),
    tax: Decimal = Decimal('0.00'),
    specifications: dict = None,
    lead_time_days: int = None,
    notes: str = "",
    recalculate: bool = True,
) -> QuotationItem:
    """
    Adds a line item to a quotation.
    Validates RFQ item alignment if linked.
    """
    # 1. RFQ Item validation
    rfq_item = None
    if rfq_item_id:
        rfq_item = RFQItem.objects.filter(pk=rfq_item_id, rfq=quotation.rfq).first()
        if not rfq_item:
            raise ValidationError({"rfq_item": ["The specified RFQ line item does not belong to this RFQ."]})

    # 2. Position auto-assignment
    if position is None:
        last_item = quotation.items.order_by('-position').first()
        position = (last_item.position + 1) if last_item else 1

    # 3. Numeric conversions & sanitization
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    disc = Decimal(str(discount or '0.00'))
    tx = Decimal(str(tax or '0.00'))

    if qty <= Decimal('0.0000'):
        raise ValidationError({"quantity": ["Quantity must be greater than zero."]})
    if price < Decimal('0.0000'):
        raise ValidationError({"unit_price": ["Unit price cannot be negative."]})
    if disc < Decimal('0.00'):
        raise ValidationError({"discount": ["Discount cannot be negative."]})
    if disc > (qty * price):
        raise ValidationError({"discount": ["Discount cannot exceed gross amount (quantity * unit_price)."]})
    if tx < Decimal('0.00'):
        raise ValidationError({"tax": ["Tax cannot be negative."]})

    calculated_line_total = max(Decimal('0.00'), ((qty * price) - disc + tx).quantize(Decimal('0.01')))

    item = QuotationItem(
        quotation=quotation,
        rfq_item=rfq_item,
        match_type=match_type,
        position=position,
        description=description.strip(),
        manufacturer=manufacturer.strip() if manufacturer else "",
        model=model.strip() if model else "",
        quantity=qty,
        unit=unit.strip() if unit else "PCS",
        unit_price=price,
        discount=disc,
        tax=tx,
        line_total=calculated_line_total,
        specifications=specifications or {},
        lead_time_days=lead_time_days,
        notes=notes.strip() if notes else "",
    )
    item.full_clean()
    item.save()

    if recalculate:
        quotation.recalculate_totals(save=True)

    return item


@transaction.atomic
def update_quotation_item(
    *,
    item: QuotationItem,
    **fields,
) -> QuotationItem:
    """
    Updates quotation line item attributes and recalculates line total and parent totals.
    """
    quotation = item.quotation

    if 'rfq_item_id' in fields:
        rfq_item_id = fields['rfq_item_id']
        if rfq_item_id:
            rfq_item = RFQItem.objects.filter(pk=rfq_item_id, rfq=quotation.rfq).first()
            if not rfq_item:
                raise ValidationError({"rfq_item": ["The specified RFQ line item does not belong to this RFQ."]})
            item.rfq_item = rfq_item
        else:
            item.rfq_item = None

    for attr in [
        'match_type',
        'position',
        'description',
        'manufacturer',
        'model',
        'unit',
        'specifications',
        'lead_time_days',
        'notes',
    ]:
        if attr in fields:
            setattr(item, attr, fields[attr])

    if 'quantity' in fields:
        item.quantity = Decimal(str(fields['quantity']))
    if 'unit_price' in fields:
        item.unit_price = Decimal(str(fields['unit_price']))
    if 'discount' in fields:
        item.discount = Decimal(str(fields['discount'] or '0.00'))
    if 'tax' in fields:
        item.tax = Decimal(str(fields['tax'] or '0.00'))

    item.line_total = item.calculate_line_total()
    item.full_clean()
    item.save()

    quotation.recalculate_totals(save=True)
    return item


@transaction.atomic
def delete_quotation_item(*, item: QuotationItem) -> None:
    """
    Deletes a line item and updates the parent quotation totals.
    """
    quotation = item.quotation
    item.delete()
    quotation.recalculate_totals(save=True)


@transaction.atomic
def create_quotation_document(
    *,
    quotation: Quotation,
    file_obj,
    user,
) -> QuotationDocument:
    """
    Validates, sanitizes, and securely stores an uploaded quotation document.
    """
    metadata = validate_quotation_document_file(file_obj)

    document = QuotationDocument(
        organization=quotation.organization,
        quotation=quotation,
        file=file_obj,
        original_filename=metadata['original_filename'],
        file_type=metadata['file_type'],
        file_extension=metadata['file_extension'],
        file_size=metadata['file_size'],
        mime_type=metadata['mime_type'],
        checksum_sha256=metadata['checksum_sha256'],
        processing_status=DocumentProcessingStatus.PENDING,
        uploaded_by=user,
    )
    document.full_clean()
    document.save()

    # Link to quotation.document if not already populated
    if not quotation.document:
        quotation.document = document.file
        quotation.save(update_fields=['document', 'updated_at'])

    return document


@transaction.atomic
def delete_quotation_document(*, document: QuotationDocument) -> None:
    """
    Removes the document record and deletes the physical file from disk.
    """
    if document.file:
        document.file.delete(save=False)
    document.delete()


@transaction.atomic
def upload_quotation_with_file(
    *,
    organization,
    user,
    rfq_id: str,
    supplier_id: str,
    file_obj,
    quotation_number: str = None,
    currency: str = "USD",
    delivery_terms: str = "",
    payment_terms: str = "",
    warranty_information: str = "",
    notes: str = "",
) -> tuple[Quotation, QuotationDocument]:
    """
    High-level onboarding flow:
    Validates file, creates Quotation, attaches QuotationDocument,
    and returns both.
    """
    # 1. Pre-validate file before creating quotation
    metadata = validate_quotation_document_file(file_obj)

    # 2. Derive quotation number if omitted
    if not quotation_number or not quotation_number.strip():
        base_name = os.path.splitext(metadata['original_filename'])[0]
        clean_ref = "".join(c for c in base_name if c.isalnum() or c in '-_')[:30]
        timestamp = timezone.now().strftime("%y%m%d%H%M")
        quotation_number = f"QT-{clean_ref}-{timestamp}" if clean_ref else f"QT-{timestamp}"

    # 3. Create quotation
    quotation = create_quotation(
        organization=organization,
        user=user,
        rfq_id=rfq_id,
        supplier_id=supplier_id,
        quotation_number=quotation_number,
        currency=currency,
        status=QuotationStatus.RECEIVED,
        delivery_terms=delivery_terms,
        payment_terms=payment_terms,
        warranty_information=warranty_information,
        notes=notes,
    )

    # 4. Attach document
    document = create_quotation_document(
        quotation=quotation,
        file_obj=file_obj,
        user=user,
    )

    return quotation, document

