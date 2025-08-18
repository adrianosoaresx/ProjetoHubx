from .settings import *  # noqa: F401,F403

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "dashboard-tests",
    }
}

DASHBOARD_ENABLE_REDIS = False
