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
import os
import sys

from dispatcherd.config import setup as dispatcher_setup  # type: ignore
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pattern_service.core"

    def ready(self):
        dispatcher_config_file_path = os.getenv(
            "PATTERN_SERVICE_DISPATCHERD_CONFIG_FILE"
        )
        if dispatcher_config_file_path:
            if not os.path.isfile(dispatcher_config_file_path):
                raise RuntimeError(
                    f"The specified file '{dispatcher_config_file_path}' for dispatcherd configuration does not exist."
                )
            # Run the startup logging for dispatcherd workers
            if "worker" in sys.argv:
                from pattern_service.core.utils.logging import startup_logging

                startup_logging(logger)

            # Enable default dispatcher config
            dispatcher_setup(file_path=dispatcher_config_file_path)
