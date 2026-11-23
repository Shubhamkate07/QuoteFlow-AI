"""
Views and ViewSets for AI Quotation Extractions and Human-Review Workflows in QuoteFlow AI.
Strictly isolates all queries and mutations to the authenticated user's organization.
Enforces multi-tier RBAC for viewing, editing, reviewing, and approving extractions.
"""

import logging
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from extractions.models import ExtractionStatus, QuotationExtraction, ReviewStatus
from extractions.permissions import (
    CanApproveQuotationExtraction,
    CanReviewQuotationExtraction,
    CanViewQuotationExtraction,
)
from extractions.serializers import (
    ApplyExtractionSerializer,
    ApproveExtractionSerializer,
    MarkFieldsReviewedSerializer,
    QuotationExtractionCorrectionSerializer,
    QuotationExtractionListSerializer,
    QuotationExtractionReviewUpdateSerializer,
    QuotationExtractionSerializer,
    RejectExtractionSerializer,
    TriggerExtractionSerializer,
)
from extractions.services import QuotationExtractionService, QuotationReviewService
from extractions.tasks import run_ai_extraction_task
from organizations.selectors import get_active_organization_for_request
from quotations.models import QuotationDocument
from quotations.selectors import get_quotation_document_by_id

logger = logging.getLogger('quoteflow.extractions.views')


class QuotationExtractionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing, triggering, reviewing, and approving AI Quotation Extractions.
    Strictly tenant-isolated.
    """
    permission_classes = [permissions.IsAuthenticated, CanViewQuotationExtraction]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def _get_extraction_or_404(self, request, pk):
        org = self._get_org(request)
        try:
            return QuotationExtraction.objects.select_related(
                'document', 'quotation', 'applied_by', 'reviewed_by', 'approved_by'
            ).get(id=pk, organization=org)
        except (QuotationExtraction.DoesNotExist, ValueError):
            # Fallback 1: check if pk is quotation_id
            try:
                return QuotationExtraction.objects.select_related(
                    'document', 'quotation', 'applied_by', 'reviewed_by', 'approved_by'
                ).filter(quotation_id=pk, organization=org).latest('created_at')
            except QuotationExtraction.DoesNotExist:
                pass

            # Fallback 2: check if pk is document_id
            try:
                return QuotationExtraction.objects.select_related(
                    'document', 'quotation', 'applied_by', 'reviewed_by', 'approved_by'
                ).filter(document_id=pk, organization=org).latest('created_at')
            except QuotationExtraction.DoesNotExist:
                raise NotFound("Quotation extraction not found in your organization.")

    def list(self, request):
        """
        GET /api/extractions/
        Query params: ?document=<uuid>&quotation=<uuid>&status=<status>&review_status=<review_status>&is_approved=<bool>
        """
        org = self._get_org(request)
        qs = QuotationExtraction.objects.filter(organization=org).select_related('document', 'quotation')

        document_id = request.query_params.get('document')
        if document_id:
            qs = qs.filter(document_id=document_id)

        quotation_id = request.query_params.get('quotation')
        if quotation_id:
            qs = qs.filter(quotation_id=quotation_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        review_status_filter = request.query_params.get('review_status')
        if review_status_filter:
            qs = qs.filter(review_status=review_status_filter)

        is_approved_filter = request.query_params.get('is_approved')
        if is_approved_filter is not None:
            val = is_approved_filter.lower() in ('true', '1')
            qs = qs.filter(is_approved=val)

        serializer = QuotationExtractionListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        GET /api/extractions/{id}/
        Retrieves full AI extraction details, validation flags, line items, evidence citations,
        review status, reviewer info, and recent human corrections.
        """
        extraction = self._get_extraction_or_404(request, pk)
        serializer = QuotationExtractionSerializer(extraction)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='document/(?P<document_id>[^/.]+)')
    def extract_document(self, request, document_id=None):
        """
        POST /api/extractions/document/{document_id}/
        Triggers AI extraction for a specific quotation document.
        Defaults to asynchronous background processing (HTTP 202 ACCEPTED).
        Pass ?sync=true to run synchronously and return the extraction immediately.
        """
        org = self._get_org(request)
        document = get_quotation_document_by_id(str(document_id), organization=org)
        if not document:
            raise NotFound("Quotation document not found in your organization.")

        serializer = TriggerExtractionSerializer(data=request.data or request.query_params)
        serializer.is_valid(raise_exception=True)
        is_sync = serializer.validated_data.get('sync', False) or request.query_params.get('sync') == 'true'
        model_name = serializer.validated_data.get('model')

        # Synchronous execution
        if is_sync:
            try:
                extraction = QuotationExtractionService.extract_from_document(
                    document=document,
                    user=request.user,
                    model_name=model_name,
                )
            except Exception as e:
                logger.error("Synchronous AI extraction failed for document %s: %s", document.id, e)
                return Response(
                    {'detail': f"AI extraction failed: {str(e)}", 'document_id': str(document.id)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            res_serializer = QuotationExtractionSerializer(extraction)
            return Response(res_serializer.data, status=status.HTTP_200_OK)

        # Asynchronous background execution (Default)
        try:
            async_task = run_ai_extraction_task.delay(str(document.id), str(request.user.id))
            status_url = request.build_absolute_uri(f"/api/quotations/documents/{document.id}/task-status/")
            return Response(
                {
                    'status': 'accepted',
                    'message': 'AI quotation extraction queued in background.',
                    'document_id': str(document.id),
                    'task_id': async_task.id,
                    'task_status_url': status_url,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as queue_err:
            logger.error("Failed to enqueue AI extraction for document %s: %s", document.id, queue_err)
            return Response(
                {'detail': f"Failed to enqueue extraction task: {str(queue_err)}", 'document_id': str(document.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['patch', 'post'], url_path='correct')
    def correct(self, request, pk=None):
        """
        PATCH/POST /api/extractions/{id}/correct/
        Allows human reviewers to correct supplier info, quotation totals, line items (prices,
        quantities, specifications), and commercial terms.
        Every change is logged to the audit history and deterministic validation is re-executed.
        """
        extraction = self._get_extraction_or_404(request, pk)

        # Check review permission
        perm = CanReviewQuotationExtraction()
        if not perm.has_object_permission(request, self, extraction):
            raise PermissionDenied("You do not have permission to edit or review quotation extractions.")

        serializer = QuotationExtractionReviewUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates = {k: v for k, v in serializer.validated_data.items() if k not in ('reason', 'mark_reviewed')}
        reason = serializer.validated_data.get('reason', '')
        mark_reviewed = serializer.validated_data.get('mark_reviewed', True)

        try:
            updated_extraction, created_corrections = QuotationReviewService.apply_corrections(
                extraction=extraction,
                updates=updates,
                user=request.user,
                reason=reason,
                mark_reviewed=mark_reviewed,
            )
        except Exception as e:
            logger.error("Correction failed on extraction %s: %s", extraction.id, e)
            return Response({'detail': f"Failed to apply corrections: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        res_serializer = QuotationExtractionSerializer(updated_extraction)
        return Response(
            {
                'status': 'corrected',
                'message': f"Successfully applied corrections ({len(created_corrections)} changes logged).",
                'extraction': res_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='mark-reviewed')
    def mark_reviewed(self, request, pk=None):
        """
        POST /api/extractions/{id}/mark-reviewed/
        Explicitly marks specific field paths or line items as verified by the human reviewer.
        Body: { "fields": ["supplier.supplier_name", "line_items[0].unit_price"] }
        """
        extraction = self._get_extraction_or_404(request, pk)

        perm = CanReviewQuotationExtraction()
        if not perm.has_object_permission(request, self, extraction):
            raise PermissionDenied("You do not have permission to review quotation extractions.")

        serializer = MarkFieldsReviewedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fields = serializer.validated_data['fields']
        updated_extraction = QuotationReviewService.mark_fields_reviewed(
            extraction=extraction,
            fields=fields,
            user=request.user,
        )

        return Response(
            {
                'status': 'reviewed',
                'message': f"Marked {len(fields)} fields as reviewed.",
                'reviewed_fields': updated_extraction.reviewed_fields,
                'review_status': updated_extraction.review_status,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        POST /api/extractions/{id}/approve/
        Formally approves the quotation extraction for official procurement execution.
        Requires Procurement Manager, Admin, or Owner role.
        Body (optional): { "review_notes": "All prices verified with supplier.", "apply_to_quotation": true }
        """
        extraction = self._get_extraction_or_404(request, pk)

        # Check approval permission
        perm = CanApproveQuotationExtraction()
        if not perm.has_object_permission(request, self, extraction):
            raise PermissionDenied("Only procurement managers or administrators can approve quotation extractions.")

        serializer = ApproveExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review_notes = serializer.validated_data.get('review_notes', '')
        should_apply = serializer.validated_data.get('apply_to_quotation', False)

        updated_extraction = QuotationReviewService.approve_extraction(
            extraction=extraction,
            user=request.user,
            review_notes=review_notes,
        )

        # Optionally auto-apply to Quotation
        quotation_data = None
        if should_apply and updated_extraction.quotation_id:
            try:
                quotation = QuotationExtractionService.apply_to_quotation(
                    extraction=updated_extraction,
                    user=request.user,
                )
                from quotations.serializers import QuotationDetailSerializer
                quotation_data = QuotationDetailSerializer(quotation, context={'request': request}).data
            except Exception as apply_err:
                logger.error("Auto-application to quotation failed on approval of %s: %s", extraction.id, apply_err)

        res_serializer = QuotationExtractionSerializer(updated_extraction)
        return Response(
            {
                'status': 'approved',
                'message': 'Extraction successfully approved by human reviewer.',
                'extraction': res_serializer.data,
                'quotation': quotation_data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        POST /api/extractions/{id}/reject/
        Rejects an extraction when document is illegitimate, incomplete, or corrupted.
        Body: { "reason": "Illegible scanned document; supplier requested to resubmit." }
        """
        extraction = self._get_extraction_or_404(request, pk)

        perm = CanReviewQuotationExtraction()
        if not perm.has_object_permission(request, self, extraction):
            raise PermissionDenied("You do not have permission to reject quotation extractions.")

        serializer = RejectExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']
        updated_extraction = QuotationReviewService.reject_extraction(
            extraction=extraction,
            user=request.user,
            reason=reason,
        )

        res_serializer = QuotationExtractionSerializer(updated_extraction)
        return Response(
            {
                'status': 'rejected',
                'message': 'Extraction has been marked as rejected.',
                'extraction': res_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='audit-history')
    def audit_history(self, request, pk=None):
        """
        GET /api/extractions/{id}/audit-history/
        Retrieves the complete, chronological audit history of all human corrections.
        """
        extraction = self._get_extraction_or_404(request, pk)
        corrections = extraction.corrections.select_related('corrected_by').order_by('-created_at')
        serializer = QuotationExtractionCorrectionSerializer(corrections, many=True)
        return Response(
            {
                'extraction_id': str(extraction.id),
                'corrections_count': corrections.count(),
                'corrections': serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='original-data')
    def original_data(self, request, pk=None):
        """
        GET /api/extractions/{id}/original-data/
        Returns the pristine, unedited AI extraction snapshot to distinguish AI output from human edits.
        """
        extraction = self._get_extraction_or_404(request, pk)
        return Response(
            {
                'extraction_id': str(extraction.id),
                'has_human_corrections': extraction.has_human_corrections,
                'corrections_count': extraction.corrections_count,
                'original_extracted_data': extraction.original_extracted_data or extraction.extracted_data,
                'current_working_data': extraction.extracted_data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='apply')
    def apply(self, request, pk=None):
        """
        POST /api/extractions/{id}/apply/
        Synchronizes verified AI extraction data and line items into the official Quotation record.
        """
        extraction = self._get_extraction_or_404(request, pk)

        serializer = ApplyExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        replace_items = serializer.validated_data.get('replace_items', True)

        try:
            quotation = QuotationExtractionService.apply_to_quotation(
                extraction=extraction,
                user=request.user,
                replace_items=replace_items,
            )
        except ValidationError as e:
            return Response(
                e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'detail': f"Failed to apply extraction: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        from quotations.serializers import QuotationDetailSerializer
        res_serializer = QuotationDetailSerializer(quotation, context={'request': request})
        return Response(
            {
                'status': 'applied',
                'message': 'Extraction successfully synchronized to Quotation and line items.',
                'quotation': res_serializer.data,
            },
            status=status.HTTP_200_OK,
        )
