import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PatternServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pattern_service"
