"""
Authentication & User URLs for QuoteFlow AI.
"""

from django.urls import path
from users.views import (
    RegisterView,
    LoginView,
    CustomTokenRefreshView,
    LogoutView,
    CurrentUserView,
    ChangePasswordView,
)

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='auth-token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', CurrentUserView.as_view(), name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
