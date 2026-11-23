"""
Views for Quotation Data Normalization, Exchange Rates, and Comparison Preparation.
"""
from datetime import date
from decimal import Decimal
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from organizations.selectors import get_active_organization_for_request
from quotations.models import Quotation
from extractions.models import QuotationExtraction
from rfqs.models import RFQ
from .models import (
    ExchangeRate,
    NormalizedQuotationSnapshot,
    RFQComparisonSetting,
    RFQComparisonSnapshot,
)
from .permissions import IsComparisonOrganizationMember
from .serializers import (
    CompareRFQOptionsSerializer,
    CompareRFQSpecificationsOptionsSerializer,
    EvaluateQuotationRiskOptionsSerializer,
    EvaluateRawRiskRequestSerializer,
    EvaluateRawScoringRequestSerializer,
    ExchangeRateSerializer,
    GenerateComparisonRequestSerializer,
    MatchItemSpecificationsRequestSerializer,
    NormalizedQuotationSnapshotSerializer,
    NormalizeOptionsSerializer,
    NormalizeRawDataSerializer,
    RFQComparisonSettingSerializer,
    RFQComparisonSnapshotSerializer,
    ScoreRFQOptionsSerializer,
    UpdateScoringWeightsSerializer,
)
from .services import (
    compare_rfq_quotations,
    compare_rfq_specifications,
    evaluate_quotation_risk_report,
    evaluate_rfq_quotations_risk_reports,
    generate_comprehensive_rfq_comparison,
    get_latest_rfq_comparison,
    get_or_create_rfq_comparison_setting,
    get_or_generate_comprehensive_comparison,
    get_org_exchange_rate_table,
    is_quotation_approved_or_reviewed,
    match_specifications_for_items,
    normalize_quotation_for_comparison,
    normalize_extraction_for_review,
    score_rfq_quotations,
    update_rfq_comparison_setting,
)
from .scoring.weights import DEFAULT_SCORING_WEIGHTS
from .normalization import (
    ExchangeRate as NormExchangeRate,
    ExchangeRateTable,
    QuotationNormalizationService,
)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Organization-specific Corporate Exchange Rates.
    Guarantees every exchange rate has an official documented source and date.
    """
    serializer_class = ExchangeRateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get_queryset(self):
        org = self._get_org(self.request)
        if not org:
            return ExchangeRate.objects.none()
        return ExchangeRate.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = self._get_org(self.request)
        serializer.save(
            organization=org,
            created_by=self.request.user,
        )


class NormalizeQuotationView(APIView):
    """
    GET / POST /api/comparisons/quotations/{id}/normalize/
    Returns deterministically normalized quotation data.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, quotation_id):
        org = self._get_org(request)
        quotation = get_object_or_404(
            Quotation.objects.filter(organization=org),
            id=quotation_id,
        )
        norm = normalize_quotation_for_comparison(
            quotation=quotation,
            target_currency=request.query_params.get('target_currency'),
            user=request.user,
        )
        return Response(norm.to_dict())

    def post(self, request, quotation_id):
        serializer = NormalizeOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = self._get_org(request)
        quotation = get_object_or_404(
            Quotation.objects.filter(organization=org),
            id=quotation_id,
        )

        norm = normalize_quotation_for_comparison(
            quotation=quotation,
            target_currency=data.get('target_currency'),
            conversion_date=data.get('conversion_date'),
            save_snapshot=data.get('save_snapshot', True),
            user=request.user,
        )
        return Response(norm.to_dict())


class NormalizeExtractionView(APIView):
    """
    GET /api/comparisons/extractions/{id}/normalize/
    Normalizes an in-review AI extraction document.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, extraction_id):
        org = self._get_org(request)
        extraction = get_object_or_404(
            QuotationExtraction.objects.filter(document__organization=org),
            id=extraction_id,
        )
        rfq_id = request.query_params.get('rfq_id')
        rfq = None
        if rfq_id:
            rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        norm = normalize_extraction_for_review(
            extraction=extraction,
            target_currency=request.query_params.get('target_currency'),
            rfq=rfq,
        )
        return Response(norm.to_dict())


class NormalizeRawDataView(APIView):
    """
    POST /api/comparisons/normalize-raw/
    Standalone deterministic normalization endpoint.
    Accepts raw extracted data dictionary, optional explicit exchange rates, and target units.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def post(self, request):
        serializer = NormalizeRawDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = self._get_org(request)
        # Construct exchange rate table from payload and org
        rate_table = get_org_exchange_rate_table(org) if org else ExchangeRateTable()
        for r_entry in data.get('exchange_rates', []):
            rate_table.add_rate(
                NormExchangeRate(
                    source_currency=r_entry['source_currency'],
                    target_currency=r_entry['target_currency'],
                    rate=Decimal(str(r_entry['rate'])),
                    rate_source=r_entry.get('rate_source', 'User Provided'),
                    rate_date=date.fromisoformat(r_entry['rate_date']) if 'rate_date' in r_entry else date.today(),
                    notes=r_entry.get('notes'),
                )
            )

        service = QuotationNormalizationService(exchange_rate_table=rate_table)
        norm = service.normalize(
            extracted_data=data['extracted_data'],
            target_currency=data.get('target_currency'),
            target_rfq_items=data.get('target_rfq_items'),
        )
        return Response(norm.to_dict())


class CompareRFQQuotationsView(APIView):
    """
    GET / POST /api/comparisons/rfqs/{rfq_id}/
    Comprehensive RFQ Comparison Endpoint.
    Integrates Price Comparison, Specification Matching, Risk Flags, Supplier Scoring,
    and side-by-side vendor matrix cards based on approved/reviewed quotation data.
    """
    permission_classes = [IsComparisonOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        """
        Retrieves latest comprehensive comparison results.
        Supports:
        - ?cached=true : Returns cached snapshot without recomputing.
        - ?refresh=true / ?force=true : Forces recomputation.
        - ?legacy_price=true : Returns flat PriceComparisonSummary dictionary.
        """
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        # Legacy price comparison format check
        if request.query_params.get('legacy_price', '').lower() in ('true', '1'):
            comparison_currency = request.query_params.get('comparison_currency') or rfq.currency or 'USD'
            conversion_date_raw = request.query_params.get('conversion_date')
            conversion_date = date.fromisoformat(conversion_date_raw) if conversion_date_raw else None
            include_incompatible = request.query_params.get('include_incompatible', '').lower() in ('true', '1')
            summary = compare_rfq_quotations(
                rfq=rfq,
                comparison_currency=comparison_currency,
                conversion_date=conversion_date,
                save_snapshot=True,
                user=request.user,
                organization=org,
                include_incompatible=include_incompatible,
            )
            return Response(summary.to_dict(), status=status.HTTP_200_OK)

        force_refresh = request.query_params.get('refresh', '').lower() in ('true', '1') or request.query_params.get('force', '').lower() in ('true', '1')
        approved_only_param = request.query_params.get('approved_only')
        approved_only = None
        if approved_only_param is not None:
            approved_only = approved_only_param.lower() in ('true', '1')

        comp_data = get_or_generate_comprehensive_comparison(
            rfq=rfq,
            organization=org,
            force_refresh=force_refresh,
            user=request.user,
            approved_only=approved_only,
        )
        return Response(comp_data, status=status.HTTP_200_OK)

    def post(self, request, rfq_id):
        """
        Executes and generates a comparison snapshot with explicit options payload.
        """
        serializer = GenerateComparisonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        result = generate_comprehensive_rfq_comparison(
            rfq=rfq,
            weights=data.get('weights'),
            comparison_currency=data.get('comparison_currency'),
            conversion_date=data.get('conversion_date'),
            approved_only=data.get('approved_only', True),
            include_incompatible=data.get('include_incompatible', False),
            save_snapshot=data.get('save_snapshot', True),
            user=request.user,
            organization=org,
        )
        return Response(result, status=status.HTTP_200_OK)


class RegenerateRFQComparisonView(APIView):
    """
    POST /api/comparisons/rfqs/{rfq_id}/regenerate/
    Forces recomputation of comprehensive RFQ comparison results using latest quotation data and configured weights.
    """
    permission_classes = [IsComparisonOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def post(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        result = generate_comprehensive_rfq_comparison(
            rfq=rfq,
            save_snapshot=True,
            user=request.user,
            organization=org,
        )
        return Response(result, status=status.HTTP_200_OK)


class RFQSupplierComparisonView(APIView):
    """
    GET /api/comparisons/rfqs/{rfq_id}/suppliers/
    Returns the side-by-side vendor matrix comparing all suppliers across Price, Specs, Delivery,
    Commercial Terms, Risk Flags, Approval Status, and Multi-Criteria Scores.
    """
    permission_classes = [IsComparisonOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        force_refresh = request.query_params.get('refresh', '').lower() in ('true', '1')
        comp_data = get_or_generate_comprehensive_comparison(rfq=rfq, organization=org, force_refresh=force_refresh, user=request.user)
        return Response({
            'rfq_id': str(rfq.id),
            'rfq_number': getattr(rfq, 'rfq_number', ''),
            'rfq_title': getattr(rfq, 'title', ''),
            'comparison_currency': comp_data.get('comparison_currency', 'USD'),
            'quotations_summary': comp_data.get('quotations_summary', {}),
            'supplier_comparison': comp_data.get('supplier_comparison', []),
        }, status=status.HTTP_200_OK)


class RFQPriceComparisonView(APIView):
    """
    GET /api/comparisons/rfqs/{rfq_id}/price/
    Returns detailed price comparison metrics: extended prices, subtotals, taxes, shipping,
    lowest price benchmarks, percentage variances, cherry-pick savings, and item matrices.
    """
    permission_classes = [IsComparisonOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        force_refresh = request.query_params.get('refresh', '').lower() in ('true', '1')
        comp_data = get_or_generate_comprehensive_comparison(rfq=rfq, organization=org, force_refresh=force_refresh, user=request.user)
        return Response(comp_data.get('price_comparison', {}), status=status.HTTP_200_OK)


class RFQComparisonWeightsView(APIView):
    """
    GET / PUT / POST /api/comparisons/rfqs/{rfq_id}/weights/
    Inspects or updates persistent comparison scoring weights for an RFQ.
    Enforces that weights sum strictly to 100%.
    Supports optional immediate re-generation via ?regenerate=true.
    """
    permission_classes = [IsComparisonOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        setting = get_or_create_rfq_comparison_setting(rfq=rfq, organization=org)
        return Response({
            'rfq_id': str(rfq.id),
            'rfq_number': getattr(rfq, 'rfq_number', ''),
            'weights': setting.weights,
            'default_weights': DEFAULT_SCORING_WEIGHTS.to_dict(),
            'is_customized': setting.weights != DEFAULT_SCORING_WEIGHTS.to_dict(),
            'factors': [
                {'factor': 'price', 'name': 'Price Competitiveness', 'description': 'Relative financial total vs lowest bid'},
                {'factor': 'spec_match', 'name': 'Specification Match', 'description': 'Technical compliance with required RFQ specs'},
                {'factor': 'delivery', 'name': 'Delivery Schedule', 'description': 'On-time delivery against deadline or fastest lead time'},
                {'factor': 'payment_terms', 'name': 'Payment Terms', 'description': 'Commercial payment liquidity and advance payment risk'},
                {'factor': 'warranty', 'name': 'Warranty Coverage', 'description': 'Coverage duration and post-delivery protection'},
            ],
            'approved_only': setting.approved_only,
            'comparison_currency': setting.comparison_currency,
        }, status=status.HTTP_200_OK)

    def put(self, request, rfq_id):
        return self._update_weights(request, rfq_id)

    def post(self, request, rfq_id):
        return self._update_weights(request, rfq_id)

    def _update_weights(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        serializer = UpdateScoringWeightsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        weights_data = serializer.validated_data['weights']
        regenerate = serializer.validated_data.get('regenerate', False) or (request.query_params.get('regenerate', '').lower() in ('true', '1'))

        setting = update_rfq_comparison_setting(
            rfq=rfq,
            weights=weights_data,
            user=request.user,
            organization=org,
        )

        resp_data = {
            'detail': 'Comparison weights updated successfully.',
            'rfq_id': str(rfq.id),
            'weights': setting.weights,
            'setting': RFQComparisonSettingSerializer(setting).data,
        }

        if regenerate:
            comp_result = generate_comprehensive_rfq_comparison(
                rfq=rfq,
                weights=setting.weights,
                save_snapshot=True,
                user=request.user,
                organization=org,
            )
            resp_data['comparison'] = comp_result

        return Response(resp_data, status=status.HTTP_200_OK)


class RFQComparisonHistoryView(APIView):
    """
    GET /api/comparisons/rfqs/{rfq_id}/history/
    Lists previous historical comparison snapshot runs for an RFQ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)

        qs = RFQComparisonSnapshot.objects.filter(
            organization=org,
            rfq=rfq,
        ).order_by('-created_at')

        serializer = RFQComparisonSnapshotSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MatchSpecificationsView(APIView):
    """
    POST /api/comparisons/match-specs/
    Compares technical specifications between an RFQ requirement and supplier quotation.
    Accepts either:
    - (rfq_item_id, quotation_item_id)
    - or raw dicts (rfq_specs, supplier_specs, item_name)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def post(self, request):
        serializer = MatchItemSpecificationsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = self._get_org(request)
        rfq_item_id = data.get('rfq_item_id')
        quotation_item_id = data.get('quotation_item_id')
        use_ai = data.get('use_ai', False)

        if rfq_item_id and quotation_item_id:
            from rfqs.models import RFQItem
            from quotations.models import QuotationItem

            rfq_item = get_object_or_404(RFQItem.objects.filter(rfq__organization=org), id=rfq_item_id)
            quotation_item = get_object_or_404(QuotationItem.objects.filter(quotation__organization=org), id=quotation_item_id)
            summary = match_specifications_for_items(rfq_item=rfq_item, quotation_item=quotation_item, use_ai=use_ai)
            return Response(summary.to_dict(), status=status.HTTP_200_OK)

        # Raw specs mode
        from comparisons.specs import SpecificationMatchingEngine
        engine = SpecificationMatchingEngine()
        summary = engine.compare_item_specifications(
            rfq_item_or_specs=data.get('rfq_specs', {}),
            supplier_item_or_specs=data.get('supplier_specs', {}),
            item_name=data.get('item_name', 'Line Item'),
            use_ai=use_ai,
        )
        return Response(summary.to_dict(), status=status.HTTP_200_OK)


class CompareRFQSpecificationsView(APIView):
    """
    GET / POST /api/comparisons/rfqs/{rfq_id}/specs/
    Computes specification matching matrices across all line items and supplier quotations for an RFQ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        use_ai = request.query_params.get('use_ai', '').lower() in ('true', '1')
        result = compare_rfq_specifications(rfq=rfq, organization=org, use_ai=use_ai)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        serializer = CompareRFQSpecificationsOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_ai = serializer.validated_data.get('use_ai', False)
        result = compare_rfq_specifications(rfq=rfq, organization=org, use_ai=use_ai)
        return Response(result, status=status.HTTP_200_OK)


class QuotationRiskEvaluationView(APIView):
    """
    GET / POST /api/comparisons/quotations/{quotation_id}/risk-flags/
    Evaluates commercial, technical, and mathematical risk flags for a quotation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, quotation_id):
        org = self._get_org(request)
        quotation = get_object_or_404(Quotation.objects.filter(organization=org), id=quotation_id)
        from comparisons.risk import RiskEngineConfig
        report = evaluate_quotation_risk_report(quotation=quotation, rfq=quotation.rfq)
        return Response(report.to_dict(), status=status.HTTP_200_OK)

    def post(self, request, quotation_id):
        org = self._get_org(request)
        quotation = get_object_or_404(Quotation.objects.filter(organization=org), id=quotation_id)
        serializer = EvaluateQuotationRiskOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from comparisons.risk import RiskEngineConfig
        config = RiskEngineConfig.from_dict(data.get('config'))
        report = evaluate_quotation_risk_report(
            quotation=quotation,
            rfq=quotation.rfq,
            config=config,
            evaluation_date=data.get('evaluation_date'),
        )
        return Response(report.to_dict(), status=status.HTTP_200_OK)


class RFQQuotationsRiskEvaluationView(APIView):
    """
    GET / POST /api/comparisons/rfqs/{rfq_id}/risk-flags/
    Computes risk reports across all quotations submitted for an RFQ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        reports = evaluate_rfq_quotations_risk_reports(rfq=rfq, organization=org)
        return Response(reports, status=status.HTTP_200_OK)

    def post(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        serializer = EvaluateQuotationRiskOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from comparisons.risk import RiskEngineConfig
        config = RiskEngineConfig.from_dict(data.get('config'))
        reports = evaluate_rfq_quotations_risk_reports(
            rfq=rfq,
            organization=org,
            config=config,
            evaluation_date=data.get('evaluation_date'),
        )
        return Response(reports, status=status.HTTP_200_OK)


class EvaluateRawRiskView(APIView):
    """
    POST /api/comparisons/risk-flags/evaluate-raw/
    Evaluates quotation risk flags on raw JSON payloads without database persistence.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EvaluateRawRiskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from comparisons.risk import QuotationRiskEngine, RiskEngineConfig
        config = RiskEngineConfig.from_dict(data.get('config'))
        engine = QuotationRiskEngine(config=config)
        report = engine.evaluate_quotation(
            quotation_or_data=data['quotation_data'],
            rfq_or_data=data.get('rfq_data'),
            evaluation_date=data.get('evaluation_date'),
        )
        return Response(report.to_dict(), status=status.HTTP_200_OK)


class RFQSupplierScoringView(APIView):
    """
    GET / POST /api/comparisons/rfqs/{rfq_id}/scoring/
    Computes explainable multi-criteria supplier scoring across all quotations for an RFQ.
    Allows customizing weights on the fly (must total 100%).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def get(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        summary = score_rfq_quotations(rfq=rfq, organization=org)
        return Response(summary.to_dict(), status=status.HTTP_200_OK)

    def post(self, request, rfq_id):
        org = self._get_org(request)
        rfq = get_object_or_404(RFQ.objects.filter(organization=org), id=rfq_id)
        serializer = ScoreRFQOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        summary = score_rfq_quotations(
            rfq=rfq,
            weights=data.get('weights'),
            organization=org,
            evaluation_date=data.get('evaluation_date'),
        )
        return Response(summary.to_dict(), status=status.HTTP_200_OK)


class EvaluateRawScoringView(APIView):
    """
    POST /api/comparisons/scoring/evaluate-raw/
    Evaluates explainable supplier scoring on raw JSON RFQ and Quotations payloads.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EvaluateRawScoringRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from comparisons.scoring import SupplierScoringEngine
        engine = SupplierScoringEngine()
        summary = engine.score_rfq_quotations(
            rfq_or_data=data['rfq_data'],
            quotations_or_data=data['quotations_data'],
            weights=data.get('weights'),
            evaluation_date=data.get('evaluation_date'),
        )
        return Response(summary.to_dict(), status=status.HTTP_200_OK)




