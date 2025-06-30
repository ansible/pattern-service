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

from django.core.exceptions import ImproperlyConfigured
from dynaconf import Dynaconf  # type: ignore


def convert_to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("yes", "true", "1")


def override_db_setting(loaded_settings: Dynaconf):
    feature_dispatcherd = convert_to_bool(
        loaded_settings.get("FEATURE_DISPATCHERD")
    )
    if feature_dispatcherd:
        databases = loaded_settings.get("DATABASES", {})
        if databases and "default" not in databases:
            raise ImproperlyConfigured(
                "DATABASES settings must contain a 'default' key"
            )

        databases["default"] = {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": loaded_settings.get("DB_HOST", "127.0.0.1"),
            "PORT": loaded_settings.get("DB_PORT", 5432),
            "USER": loaded_settings.get("DB_USER", "postgres"),
            "PASSWORD": loaded_settings.get("DB_PASSWORD"),
            "NAME": loaded_settings.get("DB_NAME", "pattern_db"),
            "OPTIONS": {
                "sslmode": loaded_settings.get("DB_SSLMODE", default="allow"),
                "sslcert": loaded_settings.get("DB_SSLCERT", default=""),
                "sslkey": loaded_settings.get("DB_SSLKEY", default=""),
                "sslrootcert": loaded_settings.get(
                    "DB_SSLROOTCERT", default=""
                ),
            },
        }
        loaded_settings.update(
            {"DATABASES": databases},
            loader_identifier="settings:override_db_setting",
        )
