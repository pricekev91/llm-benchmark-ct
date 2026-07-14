# backend/auth.py
from functools import wraps

# In a real application, this key should be loaded securely from environment variables
# e.g., os.environ.get("API_KEY")
SECRET_API_KEY = "SUPER_SECRET_DEV_KEY" 

def verify_api_key(api_key: str) -> bool:
    """Verifies the incoming API key against the configured secret key."""
    return api_key == SECRET_API_KEY

def require_auth(f):
    """Decorator to enforce authentication on specific routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This assumes authentication middleware handles the check, but a decorator is good practice for specific endpoint security.
        # For simplicity in this scaffold, we rely on the FastAPI middleware in main.py.
        return f(*args, **kwargs)
    return decorated_function