from ansible_base.lib.dynamic_config import export  # type: ignore
from ansible_base.lib.dynamic_config import factory  # type: ignore

# Django Ansible Base Dynaconf settings
DYNACONF = factory(__name__, "PATTERN_SERVICE", settings_files=["defaults.py"])
# manipulate DYNACONF as needed
export(__name__, DYNACONF)
