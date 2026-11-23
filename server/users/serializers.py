"""
Serializers for authentication, user profiles, and registration payloads.
"""

from typing import Dict, Any
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import OrganizationMembership

User = get_user_model()


class OrganizationMembershipDetailSerializer(serializers.ModelSerializer):
    """Serializes organization membership details for the authenticated user."""
    id = serializers.UUIDField(source='organization.id', read_only=True)
    name = serializers.CharField(source='organization.name', read_only=True)
    slug = serializers.CharField(source='organization.slug', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ['id', 'name', 'slug', 'role', 'role_display', 'is_active', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Comprehensive read representation of the authenticated user with organizations."""
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'is_staff',
            'is_active',
            'date_joined',
            'organizations',
        ]
        read_only_fields = ['id', 'email', 'is_staff', 'is_active', 'date_joined']

    def get_organizations(self, obj):
        memberships = OrganizationMembership.objects.filter(
            user=obj,
            organization__is_active=True,
            is_active=True,
        ).select_related('organization')
        return OrganizationMembershipDetailSerializer(memberships, many=True).data


class UserUpdateSerializer(serializers.ModelSerializer):
    """Allows safe updates to profile fields without altering credentials."""
    class Meta:
        model = User
        fields = ['full_name']

    def validate_full_name(self, value):
        return value.strip()


class RegisterSerializer(serializers.Serializer):
    """Validates user registration with optional initial workspace provisioning."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    organization_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized_email

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Apply Django's built-in password validators
        validate_password(attrs['password'])
        return attrs


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT login serializer that uses email instead of username,
    returning both tokens and user organization context.
    """
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure email field is used for authentication
        self.fields['email'] = serializers.EmailField()
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')

        if not email or not password:
            raise serializers.ValidationError("Must include both email and password.")

        # Authenticate user
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )

        if not user:
            raise AuthenticationFailed("No active account found with the given credentials.")

        if not user.is_active:
            raise AuthenticationFailed("This user account has been deactivated.")

        refresh = self.get_token(user)

        data = {
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': UserDetailSerializer(user).data,
        }

        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Validates password modification for authenticated users."""
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "New passwords do not match."})

        user = self.context.get('request').user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "The current password provided is incorrect."})

        validate_password(attrs['new_password'], user=user)
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Validates refresh token payload for revocation."""
    refresh = serializers.CharField(required=True)
