"""
Serializers for Supplier model and input validation.
"""

from decimal import Decimal
from rest_framework import serializers
from suppliers.models import Supplier, SupplierCategory, SupplierStatus


class SupplierSerializer(serializers.ModelSerializer):
    """Read representation of a supplier."""
    id = serializers.UUIDField(read_only=True)
    organization_id = serializers.UUIDField(source='organization.id', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id',
            'organization_id',
            'organization_name',
            'company_name',
            'contact_person',
            'email',
            'phone',
            'address',
            'country',
            'gst_vat_number',
            'website',
            'category',
            'category_display',
            'notes',
            'status',
            'status_display',
            'rating',
            'created_by_email',
            'created_by_name',
            'created_at',
            'updated_at',
        ]


class SupplierCreateUpdateSerializer(serializers.Serializer):
    """Input serializer for creating or updating a supplier."""
    company_name = serializers.CharField(required=True, max_length=255)
    contact_person = serializers.CharField(required=True, max_length=255)
    email = serializers.EmailField(required=True, max_length=255)
    phone = serializers.CharField(required=False, allow_blank=True, default='', max_length=50)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    country = serializers.CharField(required=False, allow_blank=True, default='US', max_length=100)
    gst_vat_number = serializers.CharField(required=False, allow_blank=True, default='', max_length=50)
    website = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    category = serializers.ChoiceField(choices=SupplierCategory.choices, default=SupplierCategory.OTHER)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=SupplierStatus.choices, default=SupplierStatus.ACTIVE)
    rating = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=3,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('5.00'),
    )

    def validate_website(self, value):
        if not value:
            return ''
        value = value.strip()
        if value and not (value.startswith('http://') or value.startswith('https://')):
            value = 'https://' + value
        return value
