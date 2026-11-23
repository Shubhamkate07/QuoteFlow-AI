"""
URL configuration for QuoteFlow AI backend project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/auth/', include('users.urls')),
    path('api/organizations/', include('organizations.urls')),
    path('api/suppliers/', include('suppliers.urls')),
    path('api/rfqs/', include('rfqs.urls')),
    path('api/quotations/', include('quotations.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/extractions/', include('extractions.urls')),
    path('api/comparisons/', include('comparisons.urls')),
    path('api/reports/', include('reports.urls')),
]

# Serve media files (quotation PDFs, Excel uploads) and static assets during local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
