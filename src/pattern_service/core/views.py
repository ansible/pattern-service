from ansible_base.lib.utils.views.ansible_base import (  # type: ignore
    AnsibleBaseView,
)
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from pattern_service.core.models import (
    Automation,
    ControllerLabel,
    Pattern,
    PatternInstance,
    ResourceState,
    Task,
)
from pattern_service.core.serializers import (
    AutomationSerializer,
    ControllerLabelSerializer,
    PatternInstanceSerializer,
    PatternSerializer,
    ResourceStateSerializer,
    TaskSerializer,
)
from pattern_service.core.tasks.worker import create_resource_state


class CoreViewSet(AnsibleBaseView):
    pass


class PatternViewSet(CoreViewSet, ModelViewSet):
    queryset = Pattern.objects.all()
    serializer_class = PatternSerializer


class ControllerLabelViewSet(CoreViewSet, ModelViewSet):
    queryset = ControllerLabel.objects.all()
    serializer_class = ControllerLabelSerializer


class PatternInstanceViewSet(CoreViewSet, ModelViewSet):
    queryset = PatternInstance.objects.all()
    serializer_class = PatternInstanceSerializer


class AutomationViewSet(CoreViewSet, ModelViewSet):
    queryset = Automation.objects.all()
    serializer_class = AutomationSerializer


class TaskViewSet(CoreViewSet, ReadOnlyModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


@api_view(["GET"])
def ping(request):
    return Response(data={"status": "ok"}, status=200)


@api_view(["GET"])
def test(request):
    return Response(data={"hello": "world"}, status=200)


class ResourceStateList(APIView):
    def get(self, request, format=None):
        resources = ResourceState.objects.all()
        serializer = ResourceStateSerializer(resources, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = ResourceStateSerializer(data=request.data)
        if serializer.is_valid():
            resource = serializer.save()
            # submit dispatcher task
            task_id = create_resource_state(resource.id)
            ResourceState.objects.filter(pk=resource.id).update(
                task_id=task_id
            )
            resource.task_id = task_id
            serializer = ResourceStateSerializer(resource)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResourceStateDetail(APIView):
    def get_object(self, pk):
        try:
            return ResourceState.objects.get(pk=pk)
        except ResourceState.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        resource = self.get_object(pk)
        serializer = ResourceStateSerializer(resource)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        resource = self.get_object(pk)
        serializer = ResourceStateSerializer(resource, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        resource = self.get_object(pk)
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
