"""
Selectors (query & read logic) for Suppliers.
All queries are strictly scoped to the tenant organization.
"""

from django.db.models import Q, QuerySet
from suppliers.models import Supplier


def list_suppliers(
    *,
    organization,
    search: str = None,
    category: str = None,
    country: str = None,
    status: str = None,
) -> QuerySet[Supplier]:
    """
    Returns suppliers scoped strictly to the organization with filters and search.
    """
    qs = (
        Supplier.objects.filter(organization=organization)
        .select_related('created_by', 'organization')
    )

    if category and category.lower() != 'all':
        qs = qs.filter(category=category.lower())

    if country and country.upper() != 'ALL':
        qs = qs.filter(country__iexact=country.strip())

    if status and status.lower() != 'all':
        qs = qs.filter(status=status.lower())

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(company_name__icontains=search)
            | Q(contact_person__icontains=search)
            | Q(email__icontains=search)
            | Q(gst_vat_number__icontains=search)
            | Q(notes__icontains=search)
        )

    return qs.order_by('company_name', '-created_at')


def get_supplier_by_id(supplier_id: str, *, organization) -> Supplier | None:
    """
    Retrieves a single supplier scoped strictly to the organization.
    """
    return (
        Supplier.objects.filter(pk=supplier_id, organization=organization)
        .select_related('created_by', 'organization')
        .first()
    )
