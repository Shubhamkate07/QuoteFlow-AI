"""
Production settings for QuoteFlow AI.
Loaded when DJANGO_ENV='production'.
Enforces strict security, HTTPS headers, disabled browsable API, and PostgreSQL.
"""

import os
from django.core.exceptions import ImproperlyConfigured
from .base import *

DJANGO_ENV = 'production'

# ==========================================
# Debug & Secret Key Enforcement
# ==========================================
# DEBUG must strictly be False in production
DEBUG = False

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY or 'insecure' in SECRET_KEY.lower() or len(SECRET_KEY.strip()) < 32:
    raise ImproperlyConfigured(
        "A secure, unique SECRET_KEY of at least 32 characters must be set in the production environment."
    )

# ALLOWED_HOSTS must be explicitly defined
ALLOWED_HOSTS = get_env_list('ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS environment variable must be specified in production (e.g. api.quoteflow.ai)."
    )

# ==========================================
# Database Configuration (PostgreSQL Required)
# ==========================================
database_url = os.getenv('DATABASE_URL', '').strip()
if database_url and not any(ph in database_url.lower() for ph in ['paste_your', 'placeholder', 'todo']):
    from urllib.parse import urlparse, unquote
    parsed = urlparse(database_url)
    if not parsed.hostname:
        raise ImproperlyConfigured(
            f"DATABASE_URL is invalid or missing hostname. Received: '{database_url}'. "
            "Please configure the Internal Database URL from your Render PostgreSQL instance."
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(parsed.path.lstrip('/')),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname,
            'PORT': str(parsed.port or 5432),
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '600')),
            'OPTIONS': {
                'sslmode': os.getenv('DB_SSLMODE', 'require'),
            },
        }
    }
else:
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')

    if not all([db_name, db_user, db_password, db_host]):
        raise ImproperlyConfigured(
            "Production requires PostgreSQL: either DATABASE_URL or (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST) must be defined. "
            "Please create a PostgreSQL database on Render and set its Internal Database URL in DATABASE_URL."
        )

    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '600')),
            'OPTIONS': {
                'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
            },
        }
    }

# ==========================================
# Production CORS Configuration
# ==========================================
CORS_ALLOW_ALL_ORIGINS = get_env_bool('CORS_ALLOW_ALL_ORIGINS', default=False)
cors_origins = get_env_list('CORS_ALLOWED_ORIGINS')
if not cors_origins:
    cors_origins = ['http://localhost:5173']
CORS_ALLOWED_ORIGINS = [o for o in cors_origins if '*' not in o]

# Dynamic regex matching for Vercel (*.vercel.app), Netlify (*.netlify.app), Render, and localhost
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://.*\.netlify\.app$",
    r"^https://.*\.onrender\.com$",
    r"^http://localhost(:\d+)?$",
    r"^http://127\.0\.0\.1(:\d+)?$",
]

CORS_ALLOW_CREDENTIALS = True

csrf_origins = get_env_list('CSRF_TRUSTED_ORIGINS')
if not csrf_origins:
    csrf_origins = ['https://*.vercel.app', 'https://*.netlify.app', 'https://*.onrender.com']
CSRF_TRUSTED_ORIGINS = csrf_origins

# ==========================================
# Production DRF Configuration (Strict JSON Only)
# ==========================================
# In production, disable BrowsableAPIRenderer to prevent leaking schema details
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# ==========================================
# HTTPS, Reverse Proxy & Cookie Security Headers
# ==========================================
# Inform Django that the reverse proxy (Nginx, ALB, Cloudflare) handles SSL termination
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = get_env_bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = get_env_bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = get_env_bool('CSRF_COOKIE_SECURE', default=True)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ==========================================
# High-Performance Media Serving (Nginx X-Accel-Redirect)
# ==========================================
# If True, Django authorizes downloads and delegates file streaming to Nginx
USE_X_ACCEL_REDIRECT = get_env_bool('USE_X_ACCEL_REDIRECT', default=False)

# ==========================================
# Production Celery Configuration
# ==========================================
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_CONCURRENCY = int(os.getenv('CELERY_CONCURRENCY', '4'))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # 1 task per worker prevents long OCR tasks starvation
CELERY_TASK_ACKS_LATE = True           # Re-queue tasks if worker is terminated unexpectedly
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ==========================================
# Production Logging Configuration
# ==========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'quoteflow': {
            'handlers': ['console'],
            'level': os.getenv('APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==========================================
# Error Monitoring (Sentry Integration)
# ==========================================
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
            send_default_pii=False,
        )
    except ImportError:
        pass
