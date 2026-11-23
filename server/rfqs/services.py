"""
Services (business logic & write operations) for RFQs and Items.
All state changes and multi-table operations execute within atomic transactions.
"""

from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from rfqs.models import (
    RFQ,
    RFQItem,
    RFQItemSpecification,
    RFQStatus,
    SpecificationImportance,
)


def generate_unique_rfq_number(organization) -> str:
    """
    Generates a sequential human-readable RFQ reference number like RFQ-2026-001.
    """
    year = timezone.now().year
    prefix = f"RFQ-{year}-"
    count = RFQ.objects.filter(organization=organization, rfq_number__startswith=prefix).count() + 1
    candidate = f"{prefix}{count:03d}"
    while RFQ.objects.filter(organization=organization, rfq_number=candidate).exists():
        count += 1
        candidate = f"{prefix}{count:03d}"
    return candidate


@transaction.atomic
def create_rfq(
    *,
    organization,
    user,
    title: str,
    rfq_number: str = None,
    description: str = "",
    status: str = RFQStatus.DRAFT,
    required_delivery_date=None,
    currency: str = "USD",
    notes: str = "",
    items: list = None,
) -> RFQ:
    """
    Creates an RFQ within the specified organization, optionally with initial line items.
    """
    if not rfq_number or not rfq_number.strip():
        rfq_number = generate_unique_rfq_number(organization)
    else:
        rfq_number = rfq_number.strip()
        if RFQ.objects.filter(organization=organization, rfq_number=rfq_number).exists():
            raise ValidationError(
                {"rfq_number": f'An RFQ with number "{rfq_number}" already exists in your organization.'}
            )

    rfq = RFQ.objects.create(
        organization=organization,
        created_by=user,
        rfq_number=rfq_number,
        title=title.strip(),
        description=description.strip(),
        status=status,
        required_delivery_date=required_delivery_date,
        currency=currency.strip().upper(),
        notes=notes.strip(),
    )

    if items:
        for idx, item_data in enumerate(items, start=1):
            create_rfq_item(
                rfq=rfq,
                position=item_data.get('position', idx),
                item_name=item_data['item_name'],
                quantity=item_data['quantity'],
                unit=item_data.get('unit', 'PCS'),
                description=item_data.get('description', ''),
                target_unit_price=item_data.get('target_unit_price'),
                manufacturer_preference=item_data.get('manufacturer_preference', ''),
                model_preference=item_data.get('model_preference', ''),
                required_delivery_date=item_data.get('required_delivery_date'),
                custom_specifications=item_data.get('custom_specifications', {}),
                notes=item_data.get('notes', ''),
                specifications=item_data.get('specifications', []),
            )

    return rfq


@transaction.atomic
def update_rfq(
    *,
    rfq: RFQ,
    title: str = None,
    rfq_number: str = None,
    description: str = None,
    status: str = None,
    required_delivery_date=None,
    currency: str = None,
    notes: str = None,
) -> RFQ:
    """
    Updates fields on an existing RFQ.
    """
    update_fields = ['updated_at']

    if title is not None:
        rfq.title = title.strip()
        update_fields.append('title')

    if rfq_number is not None and rfq_number.strip() != rfq.rfq_number:
        new_num = rfq_number.strip()
        if RFQ.objects.filter(organization=rfq.organization, rfq_number=new_num).exclude(pk=rfq.pk).exists():
            raise ValidationError(
                {"rfq_number": f'An RFQ with number "{new_num}" already exists in your organization.'}
            )
        rfq.rfq_number = new_num
        update_fields.append('rfq_number')

    if description is not None:
        rfq.description = description.strip()
        update_fields.append('description')

    if status is not None:
        rfq.status = status
        update_fields.append('status')

    if required_delivery_date is not None:
        rfq.required_delivery_date = required_delivery_date
        update_fields.append('required_delivery_date')

    if currency is not None:
        rfq.currency = currency.strip().upper()
        update_fields.append('currency')

    if notes is not None:
        rfq.notes = notes.strip()
        update_fields.append('notes')

    rfq.save(update_fields=update_fields)
    return rfq


@transaction.atomic
def delete_rfq(*, rfq: RFQ) -> None:
    """Deletes an RFQ and all associated line items and specifications."""
    rfq.delete()


@transaction.atomic
def create_rfq_item(
    *,
    rfq: RFQ,
    item_name: str,
    quantity: Decimal,
    unit: str = "PCS",
    position: int = None,
    description: str = "",
    target_unit_price: Decimal = None,
    manufacturer_preference: str = "",
    model_preference: str = "",
    required_delivery_date=None,
    custom_specifications: dict = None,
    notes: str = "",
    specifications: list = None,
) -> RFQItem:
    """
    Creates an individual line item for an RFQ with optional specifications.
    """
    if quantity <= 0:
        raise ValidationError({"quantity": "Item quantity must be strictly greater than zero."})

    if position is None:
        max_pos = RFQItem.objects.filter(rfq=rfq).aggregate(models.Max('position'))['position__max'] or 0
        position = max_pos + 1

    item = RFQItem.objects.create(
        rfq=rfq,
        position=position,
        item_name=item_name.strip(),
        description=description.strip(),
        quantity=quantity,
        unit=unit.strip().upper() if unit else 'PCS',
        target_unit_price=target_unit_price,
        manufacturer_preference=manufacturer_preference.strip(),
        model_preference=model_preference.strip(),
        required_delivery_date=required_delivery_date,
        custom_specifications=custom_specifications or {},
        notes=notes.strip(),
    )

    if specifications:
        for spec_data in specifications:
            RFQItemSpecification.objects.create(
                item=item,
                parameter_name=spec_data['parameter_name'].strip(),
                required_value=spec_data['required_value'].strip(),
                tolerance_or_unit=spec_data.get('tolerance_or_unit', '').strip(),
                importance=spec_data.get('importance', SpecificationImportance.MANDATORY),
                notes=spec_data.get('notes', '').strip(),
            )

    return item


@transaction.atomic
def update_rfq_item(
    *,
    item: RFQItem,
    item_name: str = None,
    quantity: Decimal = None,
    unit: str = None,
    position: int = None,
    description: str = None,
    target_unit_price: Decimal = None,
    manufacturer_preference: str = None,
    model_preference: str = None,
    required_delivery_date=None,
    custom_specifications: dict = None,
    notes: str = None,
    specifications: list = None,
) -> RFQItem:
    """
    Updates an RFQ line item and optionally updates/replaces its specifications.
    """
    update_fields = ['updated_at']

    if item_name is not None:
        item.item_name = item_name.strip()
        update_fields.append('item_name')

    if quantity is not None:
        if quantity <= 0:
            raise ValidationError({"quantity": "Item quantity must be strictly greater than zero."})
        item.quantity = quantity
        update_fields.append('quantity')

    if unit is not None:
        item.unit = unit.strip().upper()
        update_fields.append('unit')

    if position is not None:
        item.position = position
        update_fields.append('position')

    if description is not None:
        item.description = description.strip()
        update_fields.append('description')

    if target_unit_price is not None:
        item.target_unit_price = target_unit_price
        update_fields.append('target_unit_price')

    if manufacturer_preference is not None:
        item.manufacturer_preference = manufacturer_preference.strip()
        update_fields.append('manufacturer_preference')

    if model_preference is not None:
        item.model_preference = model_preference.strip()
        update_fields.append('model_preference')

    if required_delivery_date is not None:
        item.required_delivery_date = required_delivery_date
        update_fields.append('required_delivery_date')

    if custom_specifications is not None:
        item.custom_specifications = custom_specifications
        update_fields.append('custom_specifications')

    if notes is not None:
        item.notes = notes.strip()
        update_fields.append('notes')

    item.save(update_fields=update_fields)

    # Replace specifications if provided as a list
    if specifications is not None:
        item.specifications.all().delete()
        for spec_data in specifications:
            RFQItemSpecification.objects.create(
                item=item,
                parameter_name=spec_data['parameter_name'].strip(),
                required_value=spec_data['required_value'].strip(),
                tolerance_or_unit=spec_data.get('tolerance_or_unit', '').strip(),
                importance=spec_data.get('importance', SpecificationImportance.MANDATORY),
                notes=spec_data.get('notes', '').strip(),
            )

    return item


@transaction.atomic
def delete_rfq_item(*, item: RFQItem) -> None:
    """Deletes an RFQ line item and its specifications."""
    item.delete()
