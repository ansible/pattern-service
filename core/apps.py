import logging

from dispatcherd.config import setup as dispatcher_setup
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        # Configure dispatcher
        dispatcher_setup(config=settings.DISPATCHER_CONFIG)
