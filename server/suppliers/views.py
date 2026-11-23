"""
ViewSets for Supplier directory management.
All endpoints are strictly scoped to the authenticated user's organization.
"""

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.core.exceptions import ValidationError

from organizations.selectors import get_active_organization_for_request
from suppliers.permissions import IsSupplierOrganizationMember
from suppliers import selectors, services
from suppliers.serializers import (
    SupplierSerializer,
    SupplierCreateUpdateSerializer,
)


class SupplierViewSet(viewsets.ViewSet):
    """
    ViewSet for Supplier directory CRUD operations.
    Strictly scoped to the tenant organization.
    """
    permission_classes = [IsSupplierOrganizationMember]

    def _get_org(self, request):
        return getattr(request, 'organization', None) or get_active_organization_for_request(request)

    def list(self, request):
        """
        GET /api/suppliers/
        Query params: ?search= &category= &country= &status= &page=
        """
        org = self._get_org(request)
        suppliers = selectors.list_suppliers(
            organization=org,
            search=request.query_params.get('search'),
            category=request.query_params.get('category'),
            country=request.query_params.get('country'),
            status=request.query_params.get('status'),
        )

        page = None
        paginator = viewsets.GenericViewSet.pagination_class()
        if paginator is not None:
            page = paginator.paginate_queryset(suppliers, request, view=self)

        if page is not None:
            serializer = SupplierSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = SupplierSerializer(suppliers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        GET /api/suppliers/{id}/
        """
        org = self._get_org(request)
        supplier = selectors.get_supplier_by_id(pk, organization=org)
        if not supplier:
            raise NotFound("Supplier not found in your organization.")

        serializer = SupplierSerializer(supplier)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        """
        POST /api/suppliers/
        """
        org = self._get_org(request)
        serializer = SupplierCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            supplier = services.create_supplier(
                organization=org,
                user=request.user,
                company_name=serializer.validated_data['company_name'],
                contact_person=serializer.validated_data['contact_person'],
                email=serializer.validated_data['email'],
                phone=serializer.validated_data.get('phone', ''),
                address=serializer.validated_data.get('address', ''),
                country=serializer.validated_data.get('country', 'US'),
                gst_vat_number=serializer.validated_data.get('gst_vat_number', ''),
                website=serializer.validated_data.get('website', ''),
                category=serializer.validated_data.get('category', 'other'),
                notes=serializer.validated_data.get('notes', ''),
                status=serializer.validated_data.get('status', 'active'),
                rating=serializer.validated_data.get('rating'),
            )
        except ValidationError as e:
            return Response(
                e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SupplierSerializer(supplier).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """PATCH /api/suppliers/{id}/"""
        return self.update(request, pk=pk, partial=True)

    def update(self, request, pk=None, partial=False):
        """PUT/PATCH /api/suppliers/{id}/"""
        org = self._get_org(request)
        supplier = selectors.get_supplier_by_id(pk, organization=org)
        if not supplier:
            raise NotFound("Supplier not found in your organization.")

        serializer = SupplierCreateUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_supplier = services.update_supplier(
                supplier=supplier,
                company_name=serializer.validated_data.get('company_name'),
                contact_person=serializer.validated_data.get('contact_person'),
                email=serializer.validated_data.get('email'),
                phone=serializer.validated_data.get('phone'),
                address=serializer.validated_data.get('address'),
                country=serializer.validated_data.get('country'),
                gst_vat_number=serializer.validated_data.get('gst_vat_number'),
                website=serializer.validated_data.get('website'),
                category=serializer.validated_data.get('category'),
                notes=serializer.validated_data.get('notes'),
                status=serializer.validated_data.get('status'),
                rating=serializer.validated_data.get('rating'),
            )
        except ValidationError as e:
            return Response(
                e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SupplierSerializer(updated_supplier).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """DELETE /api/suppliers/{id}/"""
        org = self._get_org(request)
        supplier = selectors.get_supplier_by_id(pk, organization=org)
        if not supplier:
            raise NotFound("Supplier not found in your organization.")

        services.delete_supplier(supplier=supplier)
        return Response(status=status.HTTP_204_NO_CONTENT)
