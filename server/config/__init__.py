"""
Initialize Django project and expose Celery application.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
