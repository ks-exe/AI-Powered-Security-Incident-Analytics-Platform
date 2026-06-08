import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "your-secret-key-change-in-production")

# Database connection
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# Security settings
WTF_CSRF_ENABLED = True
SESSION_COOKIE_HTTPONLY = True

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Cache configuration
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
}
