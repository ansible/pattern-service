import uuid

from ansible_base.lib.utils.views.ansible_base import AnsibleBaseView
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from core import api_examples
from core.models import Automation
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.serializers import AutomationSerializer
from core.serializers import ControllerLabelSerializer
from core.serializers import PatternInstanceSerializer
from core.serializers import PatternSerializer
from core.serializers import TaskSerializer
from core.tasks.demo import sumbit_hello_world


class CoreViewSet(AnsibleBaseView):
    pass


@extend_schema_view(
    create=extend_schema(
        description="Add an Ansible pattern to the service.",
        examples=[
            api_examples.pattern_post_request,
            api_examples.pattern_post_response,
        ],
    ),
    list=extend_schema(
        description=(
            "Retrieve information about all Ansible patterns added to the service."
        ),
        examples=[api_examples.pattern_get_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single Ansible pattern by ID.",
        examples=[api_examples.pattern_get_response],
    ),
)
class PatternViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = Pattern.objects.all()
    serializer_class = PatternSerializer

    def create(self, request: Request, *args: tuple, **kwargs: dict) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pattern = serializer.save()

        task = Task.objects.create(
            status="Initiated", details={"model": "Pattern", "id": pattern.id}
        )

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "task_id": task.id,
                "message": (
                    "Pattern creation initiated. Check task status for progress."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )


@extend_schema_view(
    list=extend_schema(
        description=(
            "Retrieve information about all controller labels created by the service."
        ),
        examples=[api_examples.controller_label_get_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single controller label by ID.",
        examples=[api_examples.controller_label_get_response],
    ),
)
class ControllerLabelViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = ControllerLabel.objects.all()
    serializer_class = ControllerLabelSerializer


@extend_schema_view(
    create=extend_schema(
        description=(
            "Create an instance of an Ansible pattern, creating its defined AAP resources"
            " and saving their IDs."
        ),
        examples=[
            api_examples.pattern_instance_post_request,
            api_examples.pattern_instance_post_response,
        ],
    ),
    list=extend_schema(
        description="Retrieve information about all pattern instances.",
        examples=[api_examples.pattern_instance_get_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single pattern instance by ID.",
        examples=[api_examples.pattern_instance_get_response],
    ),
)
class PatternInstanceViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = PatternInstance.objects.all()
    serializer_class = PatternInstanceSerializer

    def create(self, request: Request, *args: tuple, **kwargs: dict) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save initial PatternInstance
        instance = serializer.save()

        # Create a Task entry to track this processing
        task = Task.objects.create(
            status="Initiated", details={"model": "PatternInstance", "id": instance.id}
        )

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "task_id": task.id,
                "message": (
                    "Pattern instance creation initiated. Check task status for progress."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )


@extend_schema_view(
    list=extend_schema(
        description="Retrieve information about all automations created by the service.",
        examples=[api_examples.automation_get_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single automation by ID.",
        examples=[api_examples.automation_get_response],
    ),
)
class AutomationViewSet(CoreViewSet, ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    queryset = Automation.objects.all()
    serializer_class = AutomationSerializer


@extend_schema_view(
    list=extend_schema(
        description="Retrieve information about all tasks created by the service.",
        examples=[api_examples.task_get_response],
    ),
    retrieve=extend_schema(
        description="Retrieve information about a single task by ID.",
        examples=[api_examples.task_get_response],
    ),
)
class TaskViewSet(CoreViewSet, ReadOnlyModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


@extend_schema(exclude=True)
@api_view(["GET"])
def ping(request: Request) -> Response:
    return Response(data={"status": "ok"}, status=200)


@extend_schema(exclude=True)
@api_view(["GET"])
def test(request: Request) -> Response:
    text = f"hello world from uuid = {uuid.uuid4()}"
    id = sumbit_hello_world(text)
    return Response(
        f"Task submitted (uuid={id}), check dispatcher logs. Should print '{text}'",
        status=200,
    )
