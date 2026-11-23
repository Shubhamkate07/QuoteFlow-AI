"""
Selectors (query & read logic) for Quotations, Line Items, and Uploaded Documents.
All queries are strictly scoped to the tenant organization.
"""

from django.db.models import Count, Q, QuerySet
from quotations.models import Quotation, QuotationItem, QuotationDocument


def list_quotations(
    *,
    organization,
    rfq_id: str = None,
    supplier_id: str = None,
    status: str = None,
    currency: str = None,
    search: str = None,
) -> QuerySet[Quotation]:
    """
    Returns quotations scoped strictly to the organization with related supplier, RFQ,
    and items/documents count annotation.
    """
    qs = (
        Quotation.objects.filter(organization=organization)
        .select_related('supplier', 'rfq', 'created_by')
        .annotate(
            items_count=Count('items', distinct=True),
            documents_count=Count('documents', distinct=True),
        )
    )

    if rfq_id:
        qs = qs.filter(rfq_id=rfq_id)

    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)

    if status:
        qs = qs.filter(status=status.lower())

    if currency:
        qs = qs.filter(currency=currency.upper())

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(quotation_number__icontains=search)
            | Q(supplier__company_name__icontains=search)
            | Q(rfq__rfq_number__icontains=search)
            | Q(rfq__title__icontains=search)
            | Q(notes__icontains=search)
        )

    return qs.order_by('-created_at')


def get_quotation_by_id(quotation_id: str, *, organization) -> Quotation | None:
    """
    Retrieves a single quotation scoped strictly to the organization
    with pre-fetched line items, documents, and supplier details.
    """
    return (
        Quotation.objects.filter(pk=quotation_id, organization=organization)
        .select_related('supplier', 'rfq', 'created_by', 'organization')
        .prefetch_related('items__rfq_item', 'documents__uploaded_by')
        .first()
    )


def list_quotation_items(*, quotation: Quotation) -> QuerySet[QuotationItem]:
    """
    Returns all line items for a quotation ordered by position.
    """
    return (
        QuotationItem.objects.filter(quotation=quotation)
        .select_related('rfq_item')
        .order_by('position')
    )


def get_quotation_item_by_id(item_id: str, *, quotation: Quotation) -> QuotationItem | None:
    """
    Retrieves a single line item belonging to a specific quotation.
    """
    return (
        QuotationItem.objects.filter(pk=item_id, quotation=quotation)
        .select_related('rfq_item')
        .first()
    )


def list_quotation_documents(*, quotation: Quotation) -> QuerySet[QuotationDocument]:
    """
    Returns all documents attached to a specific quotation ordered by upload date.
    """
    return (
        QuotationDocument.objects.filter(quotation=quotation)
        .select_related('uploaded_by')
        .order_by('-created_at')
    )


def get_quotation_document_by_id(document_id: str, *, organization) -> QuotationDocument | None:
    """
    Retrieves a single quotation document scoped strictly to the organization.
    """
    return (
        QuotationDocument.objects.filter(pk=document_id, organization=organization)
        .select_related('quotation', 'organization', 'uploaded_by')
        .first()
    )
