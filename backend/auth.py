# backend/auth.py
import os
from functools import wraps

# Load API key from environment, fall back to dev default
SECRET_API_KEY = os.environ.get("API_KEY") or "SUPER_SECRET_DEV_KEY"

# Paths exempt from authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/favicon.ico",
}

# Prefixes (checked with startswith)
PUBLIC_PREFIXES = {
    "/static/",
    "/static",
}

def verify_api_key(api_key: str) -> bool:
    """Verifies the incoming API key against the configured secret key."""
    if not api_key:
        return False
    return api_key == SECRET_API_KEY


def is_public_path(path: str) -> bool:
    """Check if a request path is exempt from authentication."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False
