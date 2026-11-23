"""
Services (business logic & write operations) for Users and Authentication.
All mutations and transactional operations reside in this layer.
"""

import uuid
from typing import Dict, Any, Tuple
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from organizations.models import Organization, OrganizationMembership, OrganizationRole

User = get_user_model()


def generate_unique_org_slug(org_name: str) -> str:
    """Generates a collision-resistant unique slug for an organization."""
    base_slug = slugify(org_name) or "workspace"
    slug = base_slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        counter += 1
    return slug


@transaction.atomic
def register_user_with_organization(
    *,
    email: str,
    password: str,
    full_name: str = "",
    organization_name: str = "",
) -> Tuple[User, Organization, Dict[str, str]]:
    """
    Registers a new user and provisions their initial organization with Owner role.
    All database operations execute atomically.
    Returns: (user, organization, tokens_dict)
    """
    email = email.strip().lower()

    # Enforce Django password validation rules
    validate_password(password)

    # 1. Create the User
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name.strip(),
    )

    # 2. Provision initial Organization
    org_title = organization_name.strip() if organization_name else f"{full_name or email.split('@')[0]}'s Workspace"
    org_slug = generate_unique_org_slug(org_title)

    organization = Organization.objects.create(
        name=org_title,
        slug=org_slug,
        created_by=user,
    )

    # 3. Create Owner Membership
    OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=OrganizationRole.OWNER,
        is_active=True,
    )

    # 4. Generate initial JWT token pair
    refresh = RefreshToken.for_user(user)
    tokens = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }

    return user, organization, tokens


def change_user_password(*, user: User, old_password: str, new_password: str) -> None:
    """
    Validates the current password and sets a new password for the authenticated user.
    """
    if not user.check_password(old_password):
        raise ValidationError({'old_password': 'The current password provided is incorrect.'})

    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=['password'])


def blacklist_refresh_token(*, refresh_token_str: str) -> None:
    """
    Blacklists a refresh token so it cannot be used to issue new access tokens.
    """
    try:
        token = RefreshToken(refresh_token_str)
        token.blacklist()
    except TokenError as e:
        raise ValidationError({'refresh': f'Invalid or expired token: {str(e)}'})
