"""
Serializers for Quotation Normalization and Corporate Exchange Rates.
"""
from rest_framework import serializers
from .models import (
    ExchangeRate,
    NormalizedQuotationSnapshot,
    RFQComparisonSetting,
    RFQComparisonSnapshot,
)


class ExchangeRateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = ExchangeRate
        fields = [
            'id',
            'organization',
            'source_currency',
            'target_currency',
            'rate',
            'rate_source',
            'rate_date',
            'notes',
            'created_by',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_at', 'updated_at']

    def validate_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError("Exchange rate must be strictly positive.")
        return value

    def validate_rate_source(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Rate source is required. Exchange rates must never be invented.")
        return value.strip()


class NormalizedQuotationSnapshotSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = NormalizedQuotationSnapshot
        fields = [
            'id',
            'quotation',
            'rfq',
            'native_currency',
            'normalized_currency',
            'exchange_rate_applied',
            'rate_source',
            'rate_date',
            'normalized_grand_total',
            'normalized_data',
            'created_by',
            'created_by_email',
            'created_at',
        ]
        read_only_fields = fields


class NormalizeOptionsSerializer(serializers.Serializer):
    target_currency = serializers.CharField(max_length=3, required=False, allow_blank=True)
    conversion_date = serializers.DateField(required=False, allow_null=True)
    save_snapshot = serializers.BooleanField(default=True)


class NormalizeRawDataSerializer(serializers.Serializer):
    extracted_data = serializers.DictField(required=True)
    target_currency = serializers.CharField(max_length=3, required=False, allow_blank=True)
    target_rfq_items = serializers.ListField(child=serializers.DictField(), required=False)
    exchange_rates = serializers.ListField(child=serializers.DictField(), required=False)


class CompareRFQOptionsSerializer(serializers.Serializer):
    """Options for executing RFQ quotation comparison."""
    comparison_currency = serializers.CharField(max_length=3, required=False, allow_blank=True)
    conversion_date = serializers.DateField(required=False, allow_null=True)
    save_snapshot = serializers.BooleanField(default=True)
    include_incompatible = serializers.BooleanField(default=False)


class RFQComparisonSnapshotSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    rfq_number = serializers.CharField(source='rfq.rfq_number', read_only=True)

    class Meta:
        model = RFQComparisonSnapshot
        fields = [
            'id',
            'rfq',
            'rfq_number',
            'comparison_currency',
            'quotations_count',
            'lowest_grand_total',
            'highest_grand_total',
            'potential_savings',
            'cherry_pick_total',
            'cherry_pick_savings',
            'weights_used',
            'approved_only_applied',
            'unreviewed_quotations_count',
            'summary_data',
            'created_by',
            'created_by_email',
            'created_at',
        ]
        read_only_fields = fields


class MatchItemSpecificationsRequestSerializer(serializers.Serializer):
    """
    Serializer for standalone or item-level specification comparison requests.
    Supports either database model IDs (rfq_item_id, quotation_item_id) or raw dictionaries.
    """
    rfq_item_id = serializers.UUIDField(required=False, allow_null=True)
    quotation_item_id = serializers.UUIDField(required=False, allow_null=True)
    rfq_specs = serializers.DictField(required=False, default=dict)
    supplier_specs = serializers.DictField(required=False, default=dict)
    item_name = serializers.CharField(max_length=255, required=False, default="Line Item")
    use_ai = serializers.BooleanField(default=False)

    def validate(self, attrs):
        has_ids = bool(attrs.get('rfq_item_id') and attrs.get('quotation_item_id'))
        has_dicts = bool(attrs.get('rfq_specs') or attrs.get('supplier_specs'))
        if not has_ids and not has_dicts:
            raise serializers.ValidationError(
                "Either provide (rfq_item_id, quotation_item_id) or raw (rfq_specs, supplier_specs) dictionaries."
            )
        return attrs


class CompareRFQSpecificationsOptionsSerializer(serializers.Serializer):
    """Options for executing multi-supplier RFQ specification comparison."""
    use_ai = serializers.BooleanField(default=False)


class EvaluateQuotationRiskOptionsSerializer(serializers.Serializer):
    """Options for quotation risk flag evaluation."""
    config = serializers.DictField(required=False, default=dict)
    evaluation_date = serializers.DateField(required=False, allow_null=True)


class EvaluateRawRiskRequestSerializer(serializers.Serializer):
    """Request payload for standalone/raw risk flag evaluation."""
    quotation_data = serializers.DictField(required=True)
    rfq_data = serializers.DictField(required=False, default=dict)
    config = serializers.DictField(required=False, default=dict)
    evaluation_date = serializers.DateField(required=False, allow_null=True)


class ScoreRFQOptionsSerializer(serializers.Serializer):
    """Options for executing explainable multi-supplier scoring."""
    weights = serializers.DictField(required=False, allow_null=True)
    evaluation_date = serializers.DateField(required=False, allow_null=True)

    def validate_weights(self, value):
        if value is not None:
            from comparisons.scoring.weights import validate_weights, WeightValidationError
            try:
                validate_weights(value)
            except WeightValidationError as e:
                raise serializers.ValidationError(str(e))
        return value


class EvaluateRawScoringRequestSerializer(serializers.Serializer):
    """Request payload for standalone/raw supplier scoring evaluation."""
    rfq_data = serializers.DictField(required=True)
    quotations_data = serializers.ListField(child=serializers.DictField(), required=True)
    weights = serializers.DictField(required=False, allow_null=True)
    evaluation_date = serializers.DateField(required=False, allow_null=True)

    def validate_weights(self, value):
        if value is not None:
            from comparisons.scoring.weights import validate_weights, WeightValidationError
            try:
                validate_weights(value)
            except WeightValidationError as e:
                raise serializers.ValidationError(str(e))
        return value


class RFQComparisonSettingSerializer(serializers.ModelSerializer):
    """Serializer for RFQ comparison preferences and persistent scoring weights."""
    updated_by_email = serializers.EmailField(source='updated_by.email', read_only=True)
    rfq_number = serializers.CharField(source='rfq.rfq_number', read_only=True)

    class Meta:
        model = RFQComparisonSetting
        fields = [
            'id',
            'rfq',
            'rfq_number',
            'weights',
            'comparison_currency',
            'approved_only',
            'include_incompatible',
            'updated_by',
            'updated_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'rfq', 'rfq_number', 'updated_by', 'updated_by_email', 'created_at', 'updated_at']

    def validate_weights(self, value):
        if value:
            from comparisons.scoring.weights import validate_weights, WeightValidationError
            try:
                validate_weights(value)
            except WeightValidationError as e:
                raise serializers.ValidationError(str(e))
        return value


class UpdateScoringWeightsSerializer(serializers.Serializer):
    """Payload for updating comparison scoring weights on an RFQ."""
    weights = serializers.DictField(required=True)
    regenerate = serializers.BooleanField(default=False, help_text="Immediately recompute comparison snapshot with new weights")

    def validate_weights(self, value):
        from comparisons.scoring.weights import validate_weights, WeightValidationError
        try:
            validate_weights(value)
        except WeightValidationError as e:
            raise serializers.ValidationError(str(e))
        return value


class GenerateComparisonRequestSerializer(serializers.Serializer):
    """Payload for generating or regenerating an RFQ comparison snapshot."""
    weights = serializers.DictField(required=False, allow_null=True)
    comparison_currency = serializers.CharField(max_length=3, required=False, allow_blank=True)
    conversion_date = serializers.DateField(required=False, allow_null=True)
    approved_only = serializers.BooleanField(default=True, help_text="Only include approved/reviewed quotations")
    include_incompatible = serializers.BooleanField(default=False)
    save_snapshot = serializers.BooleanField(default=True)
    force_refresh = serializers.BooleanField(default=True)

    def validate_weights(self, value):
        if value is not None:
            from comparisons.scoring.weights import validate_weights, WeightValidationError
            try:
                validate_weights(value)
            except WeightValidationError as e:
                raise serializers.ValidationError(str(e))
        return value





