"""
Selectors (query & read logic) for RFQs and RFQ Line Items.
All queries are strictly scoped to the tenant organization.
"""

from django.db.models import Count, Q, QuerySet
from rfqs.models import RFQ, RFQItem


def list_rfqs(
    *,
    organization,
    search: str = None,
    status: str = None,
    currency: str = None,
) -> QuerySet[RFQ]:
    """
    Returns RFQs scoped strictly to the organization with items count annotation and filters.
    """
    qs = (
        RFQ.objects.filter(organization=organization)
        .select_related('created_by')
        .annotate(items_count=Count('items'))
    )

    if status:
        qs = qs.filter(status=status.lower())

    if currency:
        qs = qs.filter(currency=currency.upper())

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(rfq_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
        )

    return qs.order_by('-created_at')


def get_rfq_by_id(rfq_id: str, *, organization) -> RFQ | None:
    """
    Retrieves a single RFQ scoped strictly to the organization with pre-fetched items and specs.
    """
    return (
        RFQ.objects.filter(pk=rfq_id, organization=organization)
        .select_related('created_by', 'organization')
        .prefetch_related('items__specifications')
        .first()
    )


def list_rfq_items(*, rfq: RFQ) -> QuerySet[RFQItem]:
    """
    Returns all line items for an RFQ with specifications pre-fetched.
    """
    return (
        RFQItem.objects.filter(rfq=rfq)
        .prefetch_related('specifications')
        .order_by('position', 'item_name')
    )


def get_rfq_item_by_id(item_id: str, *, rfq: RFQ) -> RFQItem | None:
    """
    Retrieves a single line item belonging strictly to the specified RFQ.
    """
    return (
        RFQItem.objects.filter(pk=item_id, rfq=rfq)
        .prefetch_related('specifications')
        .first()
    )
