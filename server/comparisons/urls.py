"""
URLs for Quotation Comparison, Normalization, and Exchange Rates.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CompareRFQQuotationsView,
    CompareRFQSpecificationsView,
    EvaluateRawRiskView,
    EvaluateRawScoringView,
    ExchangeRateViewSet,
    MatchSpecificationsView,
    NormalizeQuotationView,
    NormalizeExtractionView,
    NormalizeRawDataView,
    QuotationRiskEvaluationView,
    RegenerateRFQComparisonView,
    RFQComparisonHistoryView,
    RFQComparisonWeightsView,
    RFQPriceComparisonView,
    RFQQuotationsRiskEvaluationView,
    RFQSupplierComparisonView,
    RFQSupplierScoringView,
)
from reports.views import ExportRFQComparisonExcelView, ExportRFQComparisonPDFView

app_name = 'comparisons'

router = DefaultRouter()
router.register(r'exchange-rates', ExchangeRateViewSet, basename='exchange-rate')

urlpatterns = [
    path('', include(router.urls)),
    path('match-specs/', MatchSpecificationsView.as_view(), name='match-specs'),
    path('risk-flags/evaluate-raw/', EvaluateRawRiskView.as_view(), name='evaluate-raw-risk'),
    path('scoring/evaluate-raw/', EvaluateRawScoringView.as_view(), name='evaluate-raw-scoring'),
    path('rfqs/<uuid:rfq_id>/', CompareRFQQuotationsView.as_view(), name='compare-rfq'),
    path('rfqs/<uuid:rfq_id>/compare/', CompareRFQQuotationsView.as_view(), name='compare-rfq-post'),
    path('rfqs/<uuid:rfq_id>/generate/', CompareRFQQuotationsView.as_view(), name='rfq-generate-comparison'),
    path('rfqs/<uuid:rfq_id>/regenerate/', RegenerateRFQComparisonView.as_view(), name='rfq-regenerate-comparison'),
    path('rfqs/<uuid:rfq_id>/suppliers/', RFQSupplierComparisonView.as_view(), name='rfq-supplier-comparison'),
    path('rfqs/<uuid:rfq_id>/price/', RFQPriceComparisonView.as_view(), name='rfq-price-comparison'),
    path('rfqs/<uuid:rfq_id>/specs/', CompareRFQSpecificationsView.as_view(), name='compare-rfq-specs'),
    path('rfqs/<uuid:rfq_id>/risk-flags/', RFQQuotationsRiskEvaluationView.as_view(), name='rfq-risk-flags'),
    path('rfqs/<uuid:rfq_id>/scoring/', RFQSupplierScoringView.as_view(), name='rfq-scoring'),
    path('rfqs/<uuid:rfq_id>/weights/', RFQComparisonWeightsView.as_view(), name='rfq-comparison-weights'),
    path('rfqs/<uuid:rfq_id>/export/excel/', ExportRFQComparisonExcelView.as_view(), name='rfq-export-excel'),
    path('rfqs/<uuid:rfq_id>/export/pdf/', ExportRFQComparisonPDFView.as_view(), name='rfq-export-pdf'),
    path('rfqs/<uuid:rfq_id>/history/', RFQComparisonHistoryView.as_view(), name='compare-rfq-history'),
    path('quotations/<uuid:quotation_id>/normalize/', NormalizeQuotationView.as_view(), name='normalize-quotation'),
    path('quotations/<uuid:quotation_id>/risk-flags/', QuotationRiskEvaluationView.as_view(), name='quotation-risk-flags'),
    path('extractions/<uuid:extraction_id>/normalize/', NormalizeExtractionView.as_view(), name='normalize-extraction'),
    path('normalize-raw/', NormalizeRawDataView.as_view(), name='normalize-raw'),
]
