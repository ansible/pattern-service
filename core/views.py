from ansible_base.lib.utils.views.ansible_base import AnsibleBaseView
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Automation
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.serializers import AutomationSerializer
from core.serializers import ControllerLabelSerializer
from core.serializers import PatternInstanceSerializer
from core.serializers import PatternSerializer
from docs import examples


class CoreViewSet(AnsibleBaseView):
    pass


@extend_schema_view(
    create=extend_schema(
        description="Add an Ansible pattern to the service.",
        examples=[examples.pattern_post, examples.pattern_response],
    ),
    list=extend_schema(
        description="Retrieve information about all Ansible pattern added to the service.",
        examples=[examples.pattern_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single Ansible pattern by ID.",
        examples=[examples.pattern_response],
    ),
)
class PatternViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = Pattern.objects.all()
    serializer_class = PatternSerializer


@extend_schema_view(
    list=extend_schema(
        description="Retrieve information about all controller labels created by the service.",
        examples=[examples.automation_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single controller label by ID.",
        examples=[examples.automation_response],
    ),
)
class ControllerLabelViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = ControllerLabel.objects.all()
    serializer_class = ControllerLabelSerializer


@extend_schema_view(
    create=extend_schema(
        description="Create an instance of an Ansible pattern, creating its defined AAP resources and saving their IDs.",
        examples=[examples.pattern_instance_post, examples.pattern_instance_response],
    ),
    list=extend_schema(
        description="Retrieve information about all pattern instances.",
        examples=[examples.pattern_instance_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single pattern instance by ID.",
        examples=[examples.pattern_instance_response],
    ),
)
class PatternInstanceViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = PatternInstance.objects.all()
    serializer_class = PatternInstanceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Retrieve information about all automations created by the service.",
        examples=[examples.automation_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single automation by ID.",
        examples=[examples.automation_response],
    ),
)
class AutomationViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = Automation.objects.all()
    serializer_class = AutomationSerializer


@extend_schema(exclude=True)
@api_view(["GET"])
def ping(request: Request) -> Response:
    return Response(data={"status": "ok"}, status=200)


@extend_schema(exclude=True)
@api_view(["GET"])
def test(request: Request) -> Response:
    return Response(data={"hello": "world"}, status=200)
