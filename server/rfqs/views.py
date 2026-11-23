"""
Views and ViewSets for RFQs and Line Items.
Strictly scopes all queries and mutations to the authenticated user's organization.
"""

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.core.exceptions import ValidationError

from organizations.selectors import get_active_organization_for_request
from rfqs.permissions import IsRFQOrganizationMember
from rfqs import selectors, services
from rfqs.serializers import (
    RFQListSerializer,
    RFQDetailSerializer,
    RFQCreateUpdateSerializer,
    RFQItemSerializer,
    RFQItemCreateUpdateSerializer,
)


class RFQViewSet(viewsets.ViewSet):
    """
    ViewSet for managing RFQ resources scoped to the organization.
    """
    permission_classes = [IsRFQOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def list(self, request):
        """
        GET /api/rfqs/
        Query params: ?search= &status= &currency=
        """
        org = self._get_org(request)
        rfqs = selectors.list_rfqs(
            organization=org,
            search=request.query_params.get('search'),
            status=request.query_params.get('status'),
            currency=request.query_params.get('currency'),
        )

        # Standard pagination
        page = None
        paginator = viewsets.GenericViewSet.pagination_class()
        if paginator is not None:
            page = paginator.paginate_queryset(rfqs, request, view=self)

        if page is not None:
            serializer = RFQListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = RFQListSerializer(rfqs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        GET /api/rfqs/{id}/
        """
        org = self._get_org(request)
        rfq = selectors.get_rfq_by_id(pk, organization=org)
        if not rfq:
            raise NotFound("RFQ not found in your organization.")

        serializer = RFQDetailSerializer(rfq)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        """
        POST /api/rfqs/
        """
        org = self._get_org(request)
        serializer = RFQCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rfq = services.create_rfq(
                organization=org,
                user=request.user,
                title=serializer.validated_data['title'],
                rfq_number=serializer.validated_data.get('rfq_number'),
                description=serializer.validated_data.get('description', ''),
                status=serializer.validated_data.get('status', 'draft'),
                required_delivery_date=serializer.validated_data.get('required_delivery_date'),
                currency=serializer.validated_data.get('currency', 'USD'),
                notes=serializer.validated_data.get('notes', ''),
                items=serializer.validated_data.get('items', []),
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Reload with pre-fetched relations
        detailed_rfq = selectors.get_rfq_by_id(rfq.id, organization=org)
        return Response(RFQDetailSerializer(detailed_rfq).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """
        PATCH /api/rfqs/{id}/
        """
        return self.update(request, pk=pk, partial=True)

    def update(self, request, pk=None, partial=False):
        """
        PUT/PATCH /api/rfqs/{id}/
        """
        org = self._get_org(request)
        rfq = selectors.get_rfq_by_id(pk, organization=org)
        if not rfq:
            raise NotFound("RFQ not found in your organization.")

        serializer = RFQCreateUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_rfq = services.update_rfq(
                rfq=rfq,
                title=serializer.validated_data.get('title'),
                rfq_number=serializer.validated_data.get('rfq_number'),
                description=serializer.validated_data.get('description'),
                status=serializer.validated_data.get('status'),
                required_delivery_date=serializer.validated_data.get('required_delivery_date'),
                currency=serializer.validated_data.get('currency'),
                notes=serializer.validated_data.get('notes'),
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        detailed_rfq = selectors.get_rfq_by_id(updated_rfq.id, organization=org)
        return Response(RFQDetailSerializer(detailed_rfq).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """
        DELETE /api/rfqs/{id}/
        """
        org = self._get_org(request)
        rfq = selectors.get_rfq_by_id(pk, organization=org)
        if not rfq:
            raise NotFound("RFQ not found in your organization.")

        services.delete_rfq(rfq=rfq)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RFQItemViewSet(viewsets.ViewSet):
    """
    ViewSet for managing line items nested under an RFQ.
    """
    permission_classes = [IsRFQOrganizationMember]

    def _get_rfq(self, request, rfq_pk):
        org = getattr(request, 'organization', None) or get_active_organization_for_request(request)
        rfq = selectors.get_rfq_by_id(rfq_pk, organization=org)
        if not rfq:
            raise NotFound("RFQ not found in your organization.")
        return rfq

    def list(self, request, rfq_pk=None):
        """
        GET /api/rfqs/{rfq_pk}/items/
        """
        rfq = self._get_rfq(request, rfq_pk)
        items = selectors.list_rfq_items(rfq=rfq)
        serializer = RFQItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, rfq_pk=None, pk=None):
        """
        GET /api/rfqs/{rfq_pk}/items/{id}/
        """
        rfq = self._get_rfq(request, rfq_pk)
        item = selectors.get_rfq_item_by_id(pk, rfq=rfq)
        if not item:
            raise NotFound("RFQ line item not found.")

        serializer = RFQItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, rfq_pk=None):
        """
        POST /api/rfqs/{rfq_pk}/items/
        """
        rfq = self._get_rfq(request, rfq_pk)
        serializer = RFQItemCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = services.create_rfq_item(
                rfq=rfq,
                item_name=serializer.validated_data['item_name'],
                quantity=serializer.validated_data['quantity'],
                unit=serializer.validated_data.get('unit', 'PCS'),
                position=serializer.validated_data.get('position'),
                description=serializer.validated_data.get('description', ''),
                target_unit_price=serializer.validated_data.get('target_unit_price'),
                manufacturer_preference=serializer.validated_data.get('manufacturer_preference', ''),
                model_preference=serializer.validated_data.get('model_preference', ''),
                required_delivery_date=serializer.validated_data.get('required_delivery_date'),
                custom_specifications=serializer.validated_data.get('custom_specifications', {}),
                notes=serializer.validated_data.get('notes', ''),
                specifications=serializer.validated_data.get('specifications', []),
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        detailed_item = selectors.get_rfq_item_by_id(item.id, rfq=rfq)
        return Response(RFQItemSerializer(detailed_item).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, rfq_pk=None, pk=None):
        """
        PATCH /api/rfqs/{rfq_pk}/items/{id}/
        """
        return self.update(request, rfq_pk=rfq_pk, pk=pk, partial=True)

    def update(self, request, rfq_pk=None, pk=None, partial=False):
        """
        PUT/PATCH /api/rfqs/{rfq_pk}/items/{id}/
        """
        rfq = self._get_rfq(request, rfq_pk)
        item = selectors.get_rfq_item_by_id(pk, rfq=rfq)
        if not item:
            raise NotFound("RFQ line item not found.")

        serializer = RFQItemCreateUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_item = services.update_rfq_item(
                item=item,
                item_name=serializer.validated_data.get('item_name'),
                quantity=serializer.validated_data.get('quantity'),
                unit=serializer.validated_data.get('unit'),
                position=serializer.validated_data.get('position'),
                description=serializer.validated_data.get('description'),
                target_unit_price=serializer.validated_data.get('target_unit_price'),
                manufacturer_preference=serializer.validated_data.get('manufacturer_preference'),
                model_preference=serializer.validated_data.get('model_preference'),
                required_delivery_date=serializer.validated_data.get('required_delivery_date'),
                custom_specifications=serializer.validated_data.get('custom_specifications'),
                notes=serializer.validated_data.get('notes'),
                specifications=serializer.validated_data.get('specifications') if 'specifications' in serializer.validated_data else None,
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        detailed_item = selectors.get_rfq_item_by_id(updated_item.id, rfq=rfq)
        return Response(RFQItemSerializer(detailed_item).data, status=status.HTTP_200_OK)

    def destroy(self, request, rfq_pk=None, pk=None):
        """
        DELETE /api/rfqs/{rfq_pk}/items/{id}/
        """
        rfq = self._get_rfq(request, rfq_pk)
        item = selectors.get_rfq_item_by_id(pk, rfq=rfq)
        if not item:
            raise NotFound("RFQ line item not found.")

        services.delete_rfq_item(item=item)
        return Response(status=status.HTTP_204_NO_CONTENT)
