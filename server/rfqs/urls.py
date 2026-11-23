"""
URL routes for RFQs and Line Items.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rfqs.views import RFQViewSet, RFQItemViewSet
from quotations.views import QuotationViewSet

app_name = 'rfqs'

router = DefaultRouter()
router.register(r'', RFQViewSet, basename='rfq')

urlpatterns = [
    # Line Item nested endpoints
    path(
        '<uuid:rfq_pk>/items/',
        RFQItemViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='rfq-items-list',
    ),
    path(
        '<uuid:rfq_pk>/items/<uuid:pk>/',
        RFQItemViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='rfq-items-detail',
    ),
    # Quotations nested under RFQ: /api/rfqs/<rfq_pk>/quotations/
    path(
        '<uuid:rfq_pk>/quotations/',
        QuotationViewSet.as_view({'get': 'list_for_rfq', 'post': 'create_for_rfq'}),
        name='rfq-quotations-list',
    ),
    # Primary RFQ CRUD routes
    path('', include(router.urls)),
]
