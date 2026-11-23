from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from core.models import UUIDModel, TimeStampedModel


class UserManager(BaseUserManager):
    """Custom user manager where email is the primary login identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('An email address must be provided.')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, UUIDModel, TimeStampedModel):
    """
    Global user identity model for QuoteFlow AI.
    A user authenticates once with their email and can belong to multiple
    organizations through OrganizationMembership.
    """
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField('email address', unique=True, db_index=True)
    full_name = models.CharField('full name', max_length=255, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
