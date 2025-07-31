import os

from ansible_base.lib.dynamic_config import export
from ansible_base.lib.dynamic_config import factory
from ansible_base.lib.dynamic_config import load_envvars
from ansible_base.lib.dynamic_config import load_standard_settings_files

# Load local .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Ensure default environment mode
os.environ["PATTERN_SERVICE_MODE"] = os.environ.get(
    "PATTERN_SERVICE_MODE", "production"
)

# Django Ansible Base Dynaconf settings
DYNACONF = factory(
    __name__,
    "PATTERN_SERVICE",
    environments=("development", "production", "testing"),
    settings_files=["defaults.py"],
)
load_standard_settings_files(DYNACONF)
load_envvars(DYNACONF)
export(__name__, DYNACONF)
