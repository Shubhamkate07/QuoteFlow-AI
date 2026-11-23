"""
URL routes for Quotations, Quotation Line Items, and Quotation Documents.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from quotations.views import QuotationViewSet, QuotationItemViewSet, QuotationDocumentViewSet

app_name = 'quotations'

router = DefaultRouter()
router.register(r'', QuotationViewSet, basename='quotation')

urlpatterns = [
    # Multipart document upload to create a quotation: /api/quotations/upload/
    path(
        'upload/',
        QuotationViewSet.as_view({'post': 'upload'}),
        name='quotation-upload',
    ),
    # Quotations by RFQ convenience route: /api/quotations/rfq/<rfq_pk>/
    path(
        'rfq/<uuid:rfq_pk>/',
        QuotationViewSet.as_view({'get': 'list_for_rfq', 'post': 'create_for_rfq'}),
        name='quotations-by-rfq',
    ),
    # Standalone document detail, download, and deletion: /api/quotations/documents/<pk>/
    path(
        'documents/<uuid:pk>/',
        QuotationDocumentViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='quotation-document-detail',
    ),
    path(
        'documents/<uuid:pk>/download/',
        QuotationDocumentViewSet.as_view({'get': 'download'}),
        name='quotation-document-download',
    ),
    path(
        'documents/<uuid:pk>/extract/',
        QuotationDocumentViewSet.as_view({'post': 'extract'}),
        name='quotation-document-extract',
    ),
    path(
        'documents/<uuid:pk>/extraction/',
        QuotationDocumentViewSet.as_view({'get': 'extraction'}),
        name='quotation-document-extraction',
    ),
    path(
        'documents/<uuid:pk>/task-status/',
        QuotationDocumentViewSet.as_view({'get': 'task_status'}),
        name='quotation-document-task-status',
    ),
    # Nested line item endpoints: /api/quotations/<quotation_pk>/items/
    path(
        '<uuid:quotation_pk>/items/',
        QuotationItemViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='quotation-items-list',
    ),
    path(
        '<uuid:quotation_pk>/items/<uuid:pk>/',
        QuotationItemViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='quotation-items-detail',
    ),
    # Nested quotation document endpoints: /api/quotations/<quotation_pk>/documents/
    path(
        '<uuid:quotation_pk>/documents/',
        QuotationDocumentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='quotation-documents-list',
    ),
    # Primary Quotation CRUD routes
    path('', include(router.urls)),
]
