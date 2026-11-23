"""
Services (write/mutation logic) for Suppliers.
All mutations are wrapped in atomic transactions and enforce tenant constraints.
"""

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from suppliers.models import Supplier, SupplierCategory, SupplierStatus


@transaction.atomic
def create_supplier(
    *,
    organization,
    user,
    company_name: str,
    contact_person: str,
    email: str,
    phone: str = '',
    address: str = '',
    country: str = 'US',
    gst_vat_number: str = '',
    website: str = '',
    category: str = SupplierCategory.OTHER,
    notes: str = '',
    status: str = SupplierStatus.ACTIVE,
    rating: Decimal = None,
) -> Supplier:
    """Creates a new supplier scoped to the organization."""
    company_name = company_name.strip()
    if Supplier.objects.filter(organization=organization, company_name__iexact=company_name).exists():
        raise ValidationError({'company_name': f"A supplier named '{company_name}' already exists in your workspace."})

    supplier = Supplier.objects.create(
        organization=organization,
        company_name=company_name,
        contact_person=contact_person.strip(),
        email=email.strip().lower(),
        phone=phone.strip() if phone else '',
        address=address.strip() if address else '',
        country=country.strip().upper() if country else 'US',
        gst_vat_number=gst_vat_number.strip() if gst_vat_number else '',
        website=website.strip() if website else '',
        category=category,
        notes=notes.strip() if notes else '',
        status=status,
        rating=rating,
        created_by=user,
    )
    return supplier


@transaction.atomic
def update_supplier(
    *,
    supplier: Supplier,
    company_name: str = None,
    contact_person: str = None,
    email: str = None,
    phone: str = None,
    address: str = None,
    country: str = None,
    gst_vat_number: str = None,
    website: str = None,
    category: str = None,
    notes: str = None,
    status: str = None,
    rating: Decimal = None,
) -> Supplier:
    """Updates supplier fields."""
    update_fields = ['updated_at']

    if company_name is not None:
        clean_name = company_name.strip()
        if (
            Supplier.objects.filter(organization=supplier.organization, company_name__iexact=clean_name)
            .exclude(pk=supplier.pk)
            .exists()
        ):
            raise ValidationError({'company_name': f"A supplier named '{clean_name}' already exists in your workspace."})
        supplier.company_name = clean_name
        update_fields.append('company_name')

    if contact_person is not None:
        supplier.contact_person = contact_person.strip()
        update_fields.append('contact_person')

    if email is not None:
        supplier.email = email.strip().lower()
        update_fields.append('email')

    if phone is not None:
        supplier.phone = phone.strip()
        update_fields.append('phone')

    if address is not None:
        supplier.address = address.strip()
        update_fields.append('address')

    if country is not None:
        supplier.country = country.strip().upper()
        update_fields.append('country')

    if gst_vat_number is not None:
        supplier.gst_vat_number = gst_vat_number.strip()
        update_fields.append('gst_vat_number')

    if website is not None:
        supplier.website = website.strip()
        update_fields.append('website')

    if category is not None:
        supplier.category = category
        update_fields.append('category')

    if notes is not None:
        supplier.notes = notes.strip()
        update_fields.append('notes')

    if status is not None:
        supplier.status = status
        update_fields.append('status')

    if rating is not None:
        supplier.rating = rating
        update_fields.append('rating')

    supplier.save(update_fields=update_fields)
    return supplier


@transaction.atomic
def delete_supplier(*, supplier: Supplier) -> None:
    """Deletes a supplier."""
    supplier.delete()
