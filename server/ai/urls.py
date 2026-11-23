"""
URL routing for AI diagnostic and backend services.
"""

from django.urls import path
from ai.views import AIHealthCheckView

app_name = 'ai'

urlpatterns = [
    path('health/', AIHealthCheckView.as_view(), name='ai-health'),
]
