"""
URL configuration for AI Quotation Extractions.
"""

from rest_framework.routers import DefaultRouter
from extractions.views import QuotationExtractionViewSet

app_name = 'extractions'

router = DefaultRouter()
router.register(r'', QuotationExtractionViewSet, basename='quotation-extraction')

urlpatterns = router.urls
