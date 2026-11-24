"""
Base settings for QuoteFlow AI backend project.
Common settings shared across all environments (development, staging, production).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# BASE_DIR points to 'server' root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Preload environment variables from .env
load_dotenv(BASE_DIR / '.env')


def get_env_bool(var_name: str, default: bool = False) -> bool:
    """Parse boolean environment variables safely."""
    val = os.getenv(var_name)
    if val is None:
        return default
    return val.strip().lower() in ('true', '1', 't', 'yes', 'on')


def get_env_list(var_name: str, default: str = '') -> list[str]:
    """Parse comma-separated strings into a list of cleaned strings."""
    raw = os.getenv(var_name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# ==========================================
# Core Application Definition
# ==========================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
]

LOCAL_APPS = [
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'organizations.apps.OrganizationsConfig',
    'suppliers.apps.SuppliersConfig',
    'rfqs.apps.RfqsConfig',
    'quotations.apps.QuotationsConfig',
    'extractions.apps.ExtractionsConfig',
    'comparisons.apps.ComparisonsConfig',
    'reports.apps.ReportsConfig',
    'ai.apps.AiConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==========================================
# Middleware Configuration
# ==========================================
# NOTE: CorsMiddleware must come before CommonMiddleware to handle preflight OPTIONS
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

from corsheaders.defaults import default_headers, default_methods

CORS_ALLOW_METHODS = list(default_methods) + ['OPTIONS']
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-organization-id',
    'x-csrftoken',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = [
    'content-disposition',
    'content-length',
    'content-type',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ==========================================
# Password Validation
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==========================================
# Internationalization
# ==========================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==========================================
# Static Files & Uploaded Media Configuration
# ==========================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    # Extra static directory in development if needed
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload limits (10MB max to handle quotation PDFs and Excel files safely)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

# ==========================================
# Django REST Framework (DRF) Configuration
# ==========================================
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.getenv('DRF_PAGE_SIZE', '20')),
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',  # Essential for quotation PDF/Excel uploads
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Configured per-endpoint
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('DRF_THROTTLE_ANON', '120/minute'),
        'user': os.getenv('DRF_THROTTLE_USER', '600/minute'),
        'auth': os.getenv('DRF_THROTTLE_AUTH', '10/minute'),
        'extract': os.getenv('DRF_THROTTLE_EXTRACT', '20/minute'),
        'upload': os.getenv('DRF_THROTTLE_UPLOAD', '30/minute'),
    },
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'DATE_FORMAT': '%Y-%m-%d',
}

# ==========================================
# Global Security Baseline Headers
# ==========================================
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ==========================================
# Celery & Redis Configuration
# ==========================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', 300))  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', 240))  # 4 minutes

# Development & Testing Eager Mode:
# If True, tasks execute synchronously in-process without requiring a running Redis daemon
CELERY_TASK_ALWAYS_EAGER = get_env_bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# ==========================================
# Django REST Framework Simple JWT Configuration
# ==========================================
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('SECRET_KEY', 'django-insecure-quoteflow-ai-development-key-change-in-production'),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ==========================================
# Google Gemini AI Configuration
# ==========================================
os.environ.setdefault('GOOGLE_GENAI_API_VERSION', 'v1beta')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-3.5-flash').strip() or 'gemini-3.5-flash'
GEMINI_TIMEOUT_SECONDS = int(os.getenv('GEMINI_TIMEOUT_SECONDS', '60'))
GEMINI_MAX_RETRIES = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
GEMINI_RETRY_BACKOFF_FACTOR = float(os.getenv('GEMINI_RETRY_BACKOFF_FACTOR', '2.0'))
GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.1'))

