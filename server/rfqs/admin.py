from django.contrib import admin
from rfqs.models import RFQ, RFQItem, RFQItemSpecification


class RFQItemSpecificationInline(admin.TabularInline):
    model = RFQItemSpecification
    extra = 1
    fields = ('parameter_name', 'required_value', 'tolerance_or_unit', 'importance', 'notes')


class RFQItemInline(admin.StackedInline):
    model = RFQItem
    extra = 1
    fields = (
        ('position', 'item_name', 'quantity', 'unit'),
        ('target_unit_price', 'required_delivery_date'),
        ('manufacturer_preference', 'model_preference'),
        'description',
        'custom_specifications',
        'notes',
    )
    show_change_link = True


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = (
        'rfq_number',
        'title',
        'organization',
        'status',
        'currency',
        'required_delivery_date',
        'created_by',
        'created_at',
    )
    list_filter = ('status', 'currency', 'organization', 'created_at')
    search_fields = ('rfq_number', 'title', 'organization__name', 'description')
    ordering = ('-created_at',)
    inlines = [RFQItemInline]
    fieldsets = (
        ('Organization & Identity', {
            'fields': ('organization', 'rfq_number', 'title', 'created_by')
        }),
        ('Status & Commercial Terms', {
            'fields': ('status', 'currency', 'required_delivery_date')
        }),
        ('Details & Notes', {
            'fields': ('description', 'notes')
        }),
    )


@admin.register(RFQItem)
class RFQItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'rfq', 'position', 'quantity', 'unit', 'target_unit_price', 'required_delivery_date')
    list_filter = ('unit', 'rfq__organization', 'rfq__status')
    search_fields = ('item_name', 'description', 'rfq__rfq_number', 'manufacturer_preference', 'model_preference')
    ordering = ('rfq', 'position')
    inlines = [RFQItemSpecificationInline]


@admin.register(RFQItemSpecification)
class RFQItemSpecificationAdmin(admin.ModelAdmin):
    list_display = ('parameter_name', 'required_value', 'tolerance_or_unit', 'importance', 'item')
    list_filter = ('importance', 'item__rfq__organization')
    search_fields = ('parameter_name', 'required_value', 'item__item_name')
