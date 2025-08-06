from django.contrib.auth import get_user_model

from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import (
    OrganizationType,
    TeamType,
    UserType,
)

from .models import Organization
from .models import Team


class APIConfig(ServiceAPIConfig):
    service_type = 'pattern_service'


RESOURCE_LIST = [
    ResourceConfig(
        get_user_model(),
        shared_resource=SharedResource(serializer=UserType, is_provider=False),
        name_field='username',
    ),
    ResourceConfig(
        Team,
        shared_resource=SharedResource(serializer=TeamType, is_provider=False),
    ),
    ResourceConfig(
        Organization,
        shared_resource=SharedResource(serializer=OrganizationType, is_provider=False),
    ),
]
