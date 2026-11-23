"""
Views for Authentication and User Management.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.core.exceptions import ValidationError

from users.serializers import (
    RegisterSerializer,
    EmailTokenObtainPairSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
)
from users.services import (
    register_user_with_organization,
    change_user_password,
    blacklist_refresh_token,
)


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Registers a new user and provisions their initial company workspace with Owner role.
    Throttled to prevent account registration spam.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, organization, tokens = register_user_with_organization(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                full_name=serializer.validated_data.get('full_name', ''),
                organization_name=serializer.validated_data.get('organization_name', ''),
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Account registered successfully.',
                'user': UserDetailSerializer(user).data,
                'organization': {
                    'id': str(organization.id),
                    'name': organization.name,
                    'slug': organization.slug,
                    'role': 'owner',
                },
                'tokens': tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Authenticates a user via email and password, returning JWT access and refresh tokens
    along with user profile and associated organizations.
    Throttled against brute-force password guessing attacks.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    serializer_class = EmailTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/token/refresh/
    Takes a valid refresh token and returns a new access token (and new rotated refresh token).
    """
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Revokes the provided refresh token by adding it to the blacklist.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            blacklist_refresh_token(refresh_token_str=serializer.validated_data['refresh'])
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Successfully logged out. Refresh token revoked.'}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    GET /api/auth/me/
    Returns the authenticated user's profile and active organization memberships.

    PATCH /api/auth/me/
    Allows updating profile information (e.g. full_name).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(request.user).data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Allows an authenticated user to change their account password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            change_user_password(
                user=request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password'],
            )
        except ValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
