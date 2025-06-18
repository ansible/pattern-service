from rest_framework.viewsets import ModelViewSet
from ansible_base.lib.utils.views.ansible_base import AnsibleBaseView
from .models import Pattern, PatternInstance, ControllerLabel, Automation
from .serializers import PatternSerializer, ControllerLabelSerializer, PatternInstanceSerializer, AutomationSerializer

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
