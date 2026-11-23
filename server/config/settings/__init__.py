"""
Django settings package for QuoteFlow AI.

Dynamically loads development or production settings based on the
DJANGO_ENV environment variable (defaults to 'development').
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# BASE_DIR is the 'server' directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Preload environment variables from .env
load_dotenv(BASE_DIR / '.env')

DJANGO_ENV = os.getenv('DJANGO_ENV', 'development').strip().lower()

if DJANGO_ENV == 'production':
    from .production import *  # noqa: F403, F401
else:
    from .development import *  # noqa: F403, F401
