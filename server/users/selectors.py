"""
Selectors (query & read logic) for Users and Profiles.
Encapsulates database queries, keeping views and services side-effect free.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_by_id(user_id: str):
    """Retrieve a user by primary key with profile pre-fetched."""
    return User.objects.filter(pk=user_id).first()


def get_user_by_email(email: str):
    """Retrieve a user by email address."""
    return User.objects.filter(email__iexact=email).first()
