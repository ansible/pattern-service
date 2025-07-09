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
"""
Django settings.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/

Quick-start development settings - unsuitable for production
See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/


All settings can be overwritten via environment variables or setting files
should be listed in this file with type hints and default values.

Common settings:

The following values can be defined as well as environment variables
with the prefix PATTERN_SERVICE:

* SECRET_KEY - A Django secret key.
* SECRET_KEY_FILE - A file path to load Django secret key from.
    Example:
      export SECRET_KEY_FILE=/etc/eda
* DEBUG
* ALLOWED_HOSTS - A list of allowed hostnames or
    a comma separated string.
    Ex: export PATTERN_SERVICE_ALLOWED_HOSTS="localhost,127.0.0.1"
    Ex: export PATTERN_SERVICE_ALLOWED_HOSTS='["localhost", "127.0.0.1"]'
* SESSION_COOKIE_AGE - Session cookie expiration time

Database settings:

Optionally you can define DATABASES as an object
* DATABASES - A dict with django database settings

"""
from typing import List, Optional

DEBUG = False
ALLOWED_HOSTS: Optional[List[str]] = []
