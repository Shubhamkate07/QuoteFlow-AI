from django.urls import path
from core import views

urlpatterns = [
    path('', views.api_root, name='api-root'),
    path('health/', views.health_check, name='health-check'),
    path('dashboard/overview/', views.dashboard_overview, name='dashboard-overview'),
]
