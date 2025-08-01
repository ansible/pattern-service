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
from dynaconf import Dynaconf


def override_dispatcher_settings(loaded_settings: Dynaconf) -> None:
    databases = loaded_settings.get("DATABASES", {})
    if databases and "default" not in databases:
        raise ImproperlyConfigured("DATABASES settings must contain a 'default' key")

    db_host = loaded_settings.get("DB_HOST", "127.0.0.1")
    db_port = loaded_settings.get("DB_PORT", 5432)
    db_user = loaded_settings.get("DB_USER", "postgres")
    db_user_pass = loaded_settings.get("DB_PASSWORD")
    db_name = loaded_settings.get("DB_NAME", "pattern_db")
    db_app_name = loaded_settings.get("DB_APP_NAME", "dispatcher_pattern_service")
    db_sslmode = loaded_settings.get("DB_SSLMODE", default="allow")
    db_sslcert = loaded_settings.get("DB_SSLCERT", default="")
    db_sslkey = loaded_settings.get("DB_SSLKEY", default="")
    db_sslrootcert = loaded_settings.get("DB_SSLROOTCERT", default="")

    databases["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": db_host,
        "PORT": db_port,
        "USER": db_user,
        "PASSWORD": db_user_pass,
        "NAME": db_name,
        "OPTIONS": {
            "sslmode": db_sslmode,
            "sslcert": db_sslcert,
            "sslkey": db_sslkey,
            "sslrootcert": db_sslrootcert,
        },
    }

    dispatcher_conninfo = (
        f"dbname={db_name} user={db_user} password={db_user_pass} "
        f"host={db_host} port={db_port} application_name={db_app_name}"
    )
    dispatcher_node_id = loaded_settings.get("DISPATCHER_NODE_ID", default="")
    config = loaded_settings.get("DISPATCHER_CONFIG")
    config["brokers"]["pg_notify"]["config"].update({"conninfo": dispatcher_conninfo})
    if dispatcher_node_id:
        config["service"]["main_kwargs"]["node_id"] = dispatcher_node_id

    loaded_settings.update(
        {"DATABASES": databases, "DISPATCHER_CONFIG": config},
        loader_identifier="settings:override_dispatcher_settings",
    )
