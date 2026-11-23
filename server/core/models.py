import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    created_at and updated_at fields for auditing.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base model that provides a UUID primary key
    instead of standard sequential integers for multi-tenant safety.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """
    Composite abstract base model combining UUID primary keys
    with automated timestamp tracking.
    """
    class Meta:
        abstract = True


class TenantModel(BaseModel):
    """
    Abstract base model for all tenant-scoped resources.
    Guarantees every resource is linked to an Organization with CASCADE deletion
    and indexed foreign key to prevent cross-tenant data leaks.
    """
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True
