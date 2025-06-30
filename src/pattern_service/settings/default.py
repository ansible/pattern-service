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
from ansible_base.lib.dynamic_config import export  # type: ignore
from ansible_base.lib.dynamic_config import factory  # type: ignore
from ansible_base.lib.dynamic_config import load_envvars  # type: ignore
from ansible_base.lib.dynamic_config import (
    load_standard_settings_files,  # type: ignore
)
from ansible_base.lib.dynamic_config import (
    toggle_feature_flags,  # type: ignore
)

from .load_db import override_db_setting

# for more info please refer to https://github.com/ansible/django-ansible-base/blob/devel/docs/lib/dynamic_config.md?plain=1
DYNACONF = factory(
    __name__,
    "PATTERN_SERVICE",
    # Options passed directly to dynaconf
    environments=("production", "development"),
    settings_files=["defaults.py"],
)

load_standard_settings_files(DYNACONF)

# Load envvars at the end to allow them to override everything loaded so far
load_envvars(DYNACONF)  # load envvars prefixed with PATTERN_SERVICE
DYNACONF.load_file("core.py")  # load internal non-overwritable settings
override_db_setting(DYNACONF)

# toggle feature flags, considering flags coming from
# /etc/ansible-automation-platform/*.yaml
DYNACONF.update(
    toggle_feature_flags(DYNACONF),
    loader_identifier="settings:toggle_feature_flags",
    merge=True,
)

export(__name__, DYNACONF)  # export back to django.conf.settings
