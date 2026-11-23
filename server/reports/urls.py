"""
Procurement Reports & Exports URLs.
"""
from django.urls import path
from .views import ExportRFQComparisonExcelView, ExportRFQComparisonPDFView

app_name = 'reports'

urlpatterns = [
    path('rfqs/<uuid:rfq_id>/excel/', ExportRFQComparisonExcelView.as_view(), name='export-rfq-comparison-excel'),
    path('rfqs/<uuid:rfq_id>/pdf/', ExportRFQComparisonPDFView.as_view(), name='export-rfq-comparison-pdf'),
    path('rfqs/<uuid:rfq_id>/export/', ExportRFQComparisonExcelView.as_view(), name='export-rfq-comparison-excel-alt'),
]
