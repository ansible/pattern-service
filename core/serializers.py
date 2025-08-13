from __future__ import annotations

from typing import Any

from ansible_base.lib.serializers.common import CommonModelSerializer

from .models import Automation
from .models import ControllerLabel
from .models import Pattern
from .models import PatternInstance
from .models import Task


class PatternServiceBaseSerializer(CommonModelSerializer):

    class Meta(CommonModelSerializer.Meta):
        model = Pattern
        fields = CommonModelSerializer.Meta.fields

    def to_representation(self, instance: Any) -> Any:
        ret = super().to_representation(instance)
        username = self.context["request"].user.username or "runner"
        ret["created_by_ansible_id"] = username
        return ret


class PatternSerializer(PatternServiceBaseSerializer):
    class Meta(PatternServiceBaseSerializer.Meta):
        model = Pattern
        fields = PatternServiceBaseSerializer.Meta.fields + [
            "id",
            "collection_name",
            "collection_version",
            "collection_version_uri",
            "pattern_name",
            "pattern_definition",
        ]
        read_only_fields = ["pattern_definition", "collection_version_uri"]


class ControllerLabelSerializer(PatternServiceBaseSerializer):
    class Meta(PatternServiceBaseSerializer.Meta):
        model = ControllerLabel
        fields = CommonModelSerializer.Meta.fields + ["id", "label_id"]


class PatternInstanceSerializer(PatternServiceBaseSerializer):
    class Meta(PatternServiceBaseSerializer.Meta):
        model = PatternInstance
        fields = PatternServiceBaseSerializer.Meta.fields + [
            "id",
            "organization_id",
            "controller_project_id",
            "controller_ee_id",
            "controller_labels",
            "credentials",
            "executors",
            "pattern",
        ]
        read_only_fields = [
            "controller_project_id",
            "controller_ee_id",
            "controller_labels",
        ]


class AutomationSerializer(PatternServiceBaseSerializer):
    class Meta(PatternServiceBaseSerializer.Meta):
        model = Automation
        fields = PatternServiceBaseSerializer.Meta.fields + [
            "id",
            "automation_type",
            "automation_id",
            "primary",
            "pattern_instance",
        ]


class TaskSerializer(PatternServiceBaseSerializer):
    class Meta(PatternServiceBaseSerializer.Meta):
        model = Task
        fields = PatternServiceBaseSerializer.Meta.fields + [
            "status",
            "details",
        ]
