"""
Development settings for QuoteFlow AI.
Loaded when DJANGO_ENV='development' or by default.
Configured for local developer experience with safe fallbacks and verbose debugging.
"""

import os
import warnings
from .base import *

DJANGO_ENV = 'development'

# ==========================================
# Debug & Secret Key
# ==========================================
DEBUG = get_env_bool('DEBUG', default=True)

# In development, fall back to a development secret key with a console warning if not set
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'django-insecure-quoteflow-ai-development-fallback-key-change-in-production'
    warnings.warn(
        "Using development fallback SECRET_KEY. Configure a unique SECRET_KEY in server/.env for production.",
        RuntimeWarning,
    )

# Allowed hosts for local development and container networks
dev_hosts = get_env_list('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver,::1,backend,web')
for fallback_host in ['localhost', '127.0.0.1', 'testserver', '::1', 'backend', 'web']:
    if fallback_host not in dev_hosts:
        dev_hosts.append(fallback_host)
ALLOWED_HOSTS = dev_hosts

# ==========================================
# Database Configuration (PostgreSQL with SQLite Dev Fallback)
# ==========================================
use_sqlite = get_env_bool('USE_SQLITE', default=True)

if use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.getenv('DB_NAME', 'quoteflow_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '0')),
        }
    }

# ==========================================
# CORS Configuration (React Frontend)
# ==========================================
# In development, allow all origins and all localhost/127.0.0.1 ports (5173, 5174, 3000, etc.)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
]

from corsheaders.defaults import default_headers, default_methods

CORS_ALLOW_METHODS = list(default_methods) + ['OPTIONS']

CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-organization-id',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF Trusted Origins matching frontend origins
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ==========================================
# DRF Development Configuration
# ==========================================
# Enable Browsable API renderer in development for interactive exploration
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# Console email backend for testing email triggers locally
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==========================================
# Celery Development (Synchronous In-Process Execution)
# ==========================================
# Run Celery tasks immediately in-process without requiring a separate Redis or Celery daemon
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
