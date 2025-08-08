import logging

from dispatcherd.config import setup as dispatcher_setup
from django.apps import AppConfig
from django.conf import settings

from core.utils import validate_url

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        # List of required AAP variables
        required_vars = [
            "AAP_URL",
            "AAP_USERNAME",
            "AAP_PASSWORD",
        ]

        # Check that each required setting is defined
        missing = [var for var in required_vars if not getattr(settings, var, None)]
        if missing:
            logger.error(
                f"Missing required configuration variables: {', '.join(missing)}"
            )
            raise RuntimeError(
                f"Required AAP variable not defined: {', '.join(missing)}. "
            )

        # Validate AAP_URL
        try:
            settings.AAP_URL = validate_url(settings.AAP_URL)
        except ValueError as e:
            logger.error(f"AAP_URL validation failed: {e}")
            raise

        # Configure dispatcher
        dispatcher_setup(config=settings.DISPATCHER_CONFIG)
