from django.contrib import admin
from suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'organization',
        'contact_person',
        'email',
        'category',
        'country',
        'status',
        'rating',
        'created_at',
    )
    list_filter = ('category', 'status', 'country', 'organization')
    search_fields = ('company_name', 'contact_person', 'email', 'gst_vat_number')
    readonly_fields = ('id', 'created_at', 'updated_at')
