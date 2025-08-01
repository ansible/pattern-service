import logging

from dispatcherd import run_service
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Wrapper for worker command."""

    def handle(self, *args: tuple, **options: dict) -> None:
        logger.info("Starting Pattern service dispatcherd worker.")
        run_service()
