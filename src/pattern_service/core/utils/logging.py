#  Copyright 2025 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import logging
import platform
import sys
from importlib import metadata as importlib_metadata

from django.conf import settings


class UnconditionalLogger:
    """Log unconditional messages regardless of log level."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.unconditional_level = sys.maxsize
        self.unconditional_level_name = "ALWAYS"
        logging.addLevelName(
            self.unconditional_level,
            self.unconditional_level_name,
        )

    def log(self, *args, **kwargs):
        """Log at the unconditional level."""
        self.logger.log(self.unconditional_level, *args, **kwargs)

    def log_package_version(self, package_name: str) -> None:
        """Log the package version."""
        try:
            version = importlib_metadata.version(package_name)
            self.log(
                f"{package_name} library version: {version}",
            )
        except importlib_metadata.PackageNotFoundError:
            self.logger.error(
                "The package '%s' is not installed; returning 'unknown' "
                "version for it",
                package_name,
            )


LOGGING_PACKAGE_VERSIONS = [
    "dispatcherd",
    "django-ansible-base",
]


def startup_logging(logger: logging.Logger) -> None:
    """Log unconditional messages for startup."""
    unconditional_logger = UnconditionalLogger(logger)
    unconditional_logger.log(
        f">>> Python version: {platform.python_version()}"
    )
    unconditional_logger.log(
        f">>> Platform: {platform.platform()} {platform.architecture()}",
    )
    unconditional_logger.log(">>> Packages versions:")
    for pkg in LOGGING_PACKAGE_VERSIONS:
        unconditional_logger.log_package_version(pkg)

    # Display database settings
    unconditional_logger.log(f">>> Settings.DATABASES = {settings.DATABASES}")
