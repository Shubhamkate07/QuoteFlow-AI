"""
Views for Procurement Reports and Excel / PDF Exports.
"""
from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.selectors import get_active_organization_for_request
from rfqs.models import RFQ
from .services import (
    generate_rfq_comparison_excel_bytes,
    generate_rfq_comparison_pdf_bytes,
)


class ExportRFQComparisonExcelView(APIView):
    """
    GET /api/reports/rfqs/{rfq_id}/excel/
    Generates and downloads an executive-grade 5-sheet Excel (.xlsx) comparison workbook.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        try:
            excel_buffer = generate_rfq_comparison_excel_bytes(
                rfq=rfq,
                user=request.user,
                organization=org,
            )
        except Exception as exc:
            return Response(
                {'detail': f'Failed to generate Excel report: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        clean_rfq_num = getattr(rfq, 'rfq_number', str(rfq.id)).replace(' ', '_').replace('/', '_')
        filename = f"QuoteFlow_Comparison_{clean_rfq_num}_{timestamp}.xlsx"

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response


class ExportRFQComparisonPDFView(APIView):
    """
    GET /api/reports/rfqs/{rfq_id}/pdf/
    Generates and downloads an executive publication-grade PDF comparison report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        try:
            pdf_buffer = generate_rfq_comparison_pdf_bytes(
                rfq=rfq,
                user=request.user,
                organization=org,
            )
        except Exception as exc:
            return Response(
                {'detail': f'Failed to generate PDF report: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        clean_rfq_num = getattr(rfq, 'rfq_number', str(rfq.id)).replace(' ', '_').replace('/', '_')
        filename = f"QuoteFlow_Evaluation_{clean_rfq_num}_{timestamp}.pdf"

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response

