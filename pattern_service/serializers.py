from ansible_base.lib.serializers.common import CommonUserSerializer
from ansible_base.lib.serializers.common import NamedCommonModelSerializer
from ansible_base.rbac.api.related import RelatedAccessMixin

from .models import Organization
from .models import Team
from .models import User


class OrganizationSerializer(RelatedAccessMixin, NamedCommonModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class TeamSerializer(RelatedAccessMixin, NamedCommonModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"


class UserSerializer(CommonUserSerializer):
    class Meta:
        model = User
        exclude = (
            "user_permissions",
            "groups",
        )
