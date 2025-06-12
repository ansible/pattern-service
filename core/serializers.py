from __future__ import annotations

from rest_framework import serializers
from ansible_base.lib.serializers.common import CommonModelSerializer
from .models import Pattern, PatternInstance, ControllerLabel, Automation


class PatternSerializer(CommonModelSerializer):
    class Meta(CommonModelSerializer.Meta):
        model = Pattern
        fields = CommonModelSerializer.Meta.fields + [
            'id',
            'collection_name',
            'collection_version',
            'collection_version_uri',
            'pattern_name',
            'pattern_definition',
        ]
        read_only_fields = ['pattern_definition', 'collection_version_uri']


class ControllerLabelSerializer(CommonModelSerializer):
    class Meta(CommonModelSerializer.Meta):
        model = ControllerLabel
        fields = CommonModelSerializer.Meta.fields + ['id', 'label_id']

    def validate_label_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("label_id must be a positive integer.")
        return value


class PatternInstanceSerializer(CommonModelSerializer):
    class Meta(CommonModelSerializer.Meta):
        model = PatternInstance
        fields = CommonModelSerializer.Meta.fields + [
            'id',
            'organization_id',
            'controller_project_id',
            'controller_ee_id',
            'controller_labels',
            'credentials',
            'executors',
            'pattern',
        ]
        read_only_fields = ['controller_project_id', 'controller_ee_id', 'controller_labels']


class AutomationSerializer(CommonModelSerializer):
    class Meta(CommonModelSerializer.Meta):
        model = Automation
        fields = CommonModelSerializer.Meta.fields + [
            'id',
            'automation_type',
            'automation_id',
            'primary',
            'pattern_instance',
        ]
