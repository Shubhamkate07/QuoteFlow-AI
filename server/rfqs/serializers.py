"""
Serializers for RFQs, RFQ Line Items, and Technical Specifications.
"""

from decimal import Decimal
from rest_framework import serializers
from rfqs.models import (
    RFQ,
    RFQItem,
    RFQItemSpecification,
    RFQStatus,
    SpecificationImportance,
)


class RFQItemSpecificationSerializer(serializers.ModelSerializer):
    """Serializer for structured technical specifications on an RFQ line item."""
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = RFQItemSpecification
        fields = [
            'id',
            'parameter_name',
            'required_value',
            'tolerance_or_unit',
            'importance',
            'notes',
        ]


class RFQItemSerializer(serializers.ModelSerializer):
    """Comprehensive read representation of an RFQ line item with specifications."""
    id = serializers.UUIDField(read_only=True)
    rfq_id = serializers.UUIDField(source='rfq.id', read_only=True)
    specifications = RFQItemSpecificationSerializer(many=True, read_only=True)
    effective_delivery_date = serializers.DateField(read_only=True)

    class Meta:
        model = RFQItem
        fields = [
            'id',
            'rfq_id',
            'position',
            'item_name',
            'description',
            'quantity',
            'unit',
            'target_unit_price',
            'manufacturer_preference',
            'model_preference',
            'required_delivery_date',
            'effective_delivery_date',
            'custom_specifications',
            'notes',
            'specifications',
            'created_at',
            'updated_at',
        ]


class RFQItemCreateUpdateSerializer(serializers.Serializer):
    """Input serializer for adding or updating an RFQ line item."""
    position = serializers.IntegerField(required=False, min_value=1)
    item_name = serializers.CharField(required=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    quantity = serializers.DecimalField(required=True, max_digits=14, decimal_places=4, min_value=Decimal('0.0001'))
    unit = serializers.CharField(required=False, default='PCS', max_length=50)
    target_unit_price = serializers.DecimalField(required=False, allow_null=True, max_digits=14, decimal_places=2, min_value=Decimal('0.00'))
    manufacturer_preference = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    model_preference = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    required_delivery_date = serializers.DateField(required=False, allow_null=True)
    custom_specifications = serializers.DictField(required=False, default=dict)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    specifications = RFQItemSpecificationSerializer(many=True, required=False, default=list)


class RFQListSerializer(serializers.ModelSerializer):
    """Lightweight summary serializer for RFQ list views."""
    id = serializers.UUIDField(read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    target_budget = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            'id',
            'rfq_number',
            'title',
            'description',
            'status',
            'status_display',
            'currency',
            'required_delivery_date',
            'items_count',
            'target_budget',
            'created_by_email',
            'created_at',
            'updated_at',
        ]

    def get_target_budget(self, obj) -> float:
        from decimal import Decimal
        total = Decimal('0.00')
        for item in obj.items.all():
            if item.target_unit_price is not None and item.quantity is not None:
                total += item.target_unit_price * item.quantity
        return float(total)


class RFQDetailSerializer(serializers.ModelSerializer):
    """Detailed read representation of an RFQ including child line items."""
    id = serializers.UUIDField(read_only=True)
    items = RFQItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    target_budget = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            'id',
            'rfq_number',
            'title',
            'description',
            'status',
            'status_display',
            'currency',
            'required_delivery_date',
            'notes',
            'created_by_email',
            'items_count',
            'target_budget',
            'items',
            'created_at',
            'updated_at',
        ]

    def get_target_budget(self, obj) -> float:
        from decimal import Decimal
        total = Decimal('0.00')
        for item in obj.items.all():
            if item.target_unit_price is not None and item.quantity is not None:
                total += item.target_unit_price * item.quantity
        return float(total)

    def get_items_count(self, obj):
        return obj.items.count()


class RFQCreateUpdateSerializer(serializers.Serializer):
    """Input serializer for creating or updating an RFQ."""
    rfq_number = serializers.CharField(required=False, allow_blank=True, max_length=64)
    title = serializers.CharField(required=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=RFQStatus.choices, default=RFQStatus.DRAFT)
    required_delivery_date = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, default='USD', max_length=3)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = RFQItemCreateUpdateSerializer(many=True, required=False, default=list)

    def validate_currency(self, value):
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise serializers.ValidationError("Currency must be a 3-letter ISO code (e.g. USD, EUR, INR).")
        return normalized
