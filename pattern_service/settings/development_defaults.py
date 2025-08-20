from pathlib import Path

ALLOWED_HOSTS = ["localhost", "pattern-service", "127.0.0.1"]
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True
SECRET_KEY = "insecure"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {name} {lineno} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": DEBUG,
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "loggers": {
        "ansible_base": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "core": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "dispatcherd": {"handlers": ["console"], "level": "INFO"},
        "drf_spectacular": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

# Base URL of your AAP service
AAP_URL = "http://localhost:44926"  # or your default URL

# Whether to verify SSL certificates (True or False)
AAP_VALIDATE_CERTS = False

# Default username and password for authentication
AAP_USERNAME = "admin"
AAP_PASSWORD = "password"
