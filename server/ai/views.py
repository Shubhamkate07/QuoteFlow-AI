"""
API Views for AI integration health and backend diagnostics.
Enforces strict security: never exposes raw API keys, credentials, or secrets to the client.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.service import GeminiService


class AIHealthCheckView(APIView):
    """
    GET /api/ai/health/
    Performs a backend diagnostic check of the Gemini AI integration.
    Requires user authentication.
    Returns model name, configuration state, masked key, and latency.
    NEVER leaks or returns the raw GEMINI_API_KEY.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        service = GeminiService()
        health = service.health_check()
        http_status = status.HTTP_200_OK if health.get('status') in ('healthy', 'unconfigured') else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health, status=http_status)
