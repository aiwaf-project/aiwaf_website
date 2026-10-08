"""Settings for this standalone example, separate from your application's settings."""

from pathlib import Path

SECRET_KEY = "local-documentation-test-key"
INSTALLED_APPS = ["aiwaf.django"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# Only for this standalone fixture: create AIWAF tables without generated migrations.
MIGRATION_MODULES = {"aiwaf": None}
ROOT_URLCONF = "test_django_protection"
ALLOWED_HOSTS = ["testserver"]
MIDDLEWARE = ["aiwaf.django.middleware.RateLimitMiddleware"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "documentation-protection-tests",
    }
}
AIWAF_USE_CSV = False
AIWAF_PATH_MANIFEST = str(Path(__file__).with_name("unused-test-manifest.json"))
AIWAF_RATE_WINDOW = 60
AIWAF_RATE_MAX = 3
AIWAF_RATE_FLOOD = 100
AIWAF_EXEMPT_PATHS = ["/health"]
AIWAF_SETTINGS = {
    "PATH_RULES": [
        {"PREFIX": "/api/message", "RATE_LIMIT": {"WINDOW": 60, "MAX": 3, "FLOOD": 100}},
        {"PREFIX": "/api/preview", "DISABLE": ["rate_limit"]},
    ]
}
