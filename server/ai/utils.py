"""
Utility functions for AI services in QuoteFlow AI.
Ensures API keys, tokens, and sensitive headers are never logged or exposed.
"""

import re
from typing import Optional


# Regex pattern to match potential Google API Keys (e.g., AIzaSy...)
_API_KEY_PATTERN = re.compile(r'AIza[0-9A-Za-z\-_]{35}')


def mask_api_key(api_key: Optional[str]) -> str:
    """
    Safely masks an API key for logs and UI status displays.
    Example: 'AIzaSyD1234567890abcdef' -> 'AIza****cdef'
    """
    if not api_key:
        return "[NOT CONFIGURED]"
    
    clean_key = api_key.strip()
    if len(clean_key) <= 8:
        return "****"
    
    return f"{clean_key[:4]}****{clean_key[-4:]}"


def sanitize_log_message(message: str, secret_key: Optional[str] = None) -> str:
    """
    Removes any instances of secret API keys or Google key patterns from log strings.
    """
    if not message:
        return ""
    
    sanitized = str(message)
    
    # 1. Redact specific configured key if provided
    if secret_key and len(secret_key.strip()) > 6:
        sanitized = sanitized.replace(secret_key.strip(), "[REDACTED_API_KEY]")
    
    # 2. Redact any generic AIza Google API key pattern
    sanitized = _API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)
    
    return sanitized
