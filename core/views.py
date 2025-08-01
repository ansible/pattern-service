import uuid

from ansible_base.lib.utils.views.ansible_base import AnsibleBaseView
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.tasks.demo import sumbit_hello_world

from .models import Automation
from .models import ControllerLabel
from .models import Pattern
from .models import PatternInstance
from .models import Task
from .serializers import AutomationSerializer
from .serializers import ControllerLabelSerializer
from .serializers import PatternInstanceSerializer
from .serializers import PatternSerializer
from .serializers import TaskSerializer


class CoreViewSet(AnsibleBaseView):
    pass


class PatternViewSet(CoreViewSet, ModelViewSet):
    queryset = Pattern.objects.all()
    serializer_class = PatternSerializer

    def create(self, request: Request, *args: tuple, **kwargs: dict) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pattern = serializer.save()

        task = Task.objects.create(
            status="Initiated", details={"model": "Pattern", "id": pattern.id}
        )

        return Response(
            {
                "task_id": task.id,
                "message": (
                    "Pattern creation initiated. Check task status for progress."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ControllerLabelViewSet(CoreViewSet, ModelViewSet):
    queryset = ControllerLabel.objects.all()
    serializer_class = ControllerLabelSerializer


class PatternInstanceViewSet(CoreViewSet, ModelViewSet):
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

        return Response(
            {
                "task_id": task.id,
                "message": (
                    "PatternInstance creation initiated. Check task status for progress."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AutomationViewSet(CoreViewSet, ModelViewSet):
    queryset = Automation.objects.all()
    serializer_class = AutomationSerializer


class TaskViewSet(CoreViewSet, ReadOnlyModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


@api_view(["GET"])
def ping(request: Request) -> Response:
    return Response(data={"status": "ok"}, status=200)


@api_view(["GET"])
def test(request: Request) -> Response:
    text = f"hello world from uuid = {uuid.uuid4()}"
    id = sumbit_hello_world(text)
    return Response(
        f"Task submitted (uuid={id}), check dispatcher logs. Should print '{text}'",
        status=200,
    )
