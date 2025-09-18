from pathlib import Path

ALLOWED_HOSTS = ["localhost", "pattern-service", "127.0.0.1"]
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "insecure"

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "insecure"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    "dispatcher": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "localhost",
        "PORT": 5432,
        "PASSWORD": DB_PASSWORD,
        "NAME": DB_NAME,
    },
}

DEBUG = True

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
        "dispatcherd": {"handlers": ["console"], "level": "INFO"},
    },
}


# Base URL of your AAP service
AAP_URL = "http://localhost:44926"  # or your default URL

# Whether to verify SSL certificates (True or False)
AAP_VALIDATE_CERTS = False

# Default username and password for authentication
AAP_USERNAME = "admin"
AAP_PASSWORD = "password"
