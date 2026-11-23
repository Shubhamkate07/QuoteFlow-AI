"""
URL routes for Supplier Management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from suppliers.views import SupplierViewSet

app_name = 'suppliers'

router = DefaultRouter()
router.register(r'', SupplierViewSet, basename='supplier')

urlpatterns = [
    path('', include(router.urls)),
]
