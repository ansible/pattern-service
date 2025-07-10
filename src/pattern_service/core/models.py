from __future__ import annotations

from ansible_base.lib.abstract_models import CommonModel  # type: ignore
from django.db import models


class Pattern(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "collection_name",
                    "collection_version",
                    "pattern_name",
                ],
                name="unique_pattern_collection_version",
            )
        ]

    collection_name: models.CharField = models.CharField(max_length=200)
    collection_version: models.CharField = models.CharField(max_length=50)
    collection_version_uri: models.CharField = models.CharField(
        max_length=200, blank=True, null=True
    )
    pattern_name: models.CharField = models.CharField(max_length=200)
    pattern_definition: models.JSONField = models.JSONField(
        blank=True, null=True
    )


class ControllerLabel(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]

    label_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField(
        unique=True
    )


class PatternInstance(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "pattern"],
                name="unique_pattern_instance_organization",
            )
        ]

    organization_id: models.PositiveBigIntegerField = (
        models.PositiveBigIntegerField()
    )
    controller_project_id: models.PositiveBigIntegerField = (
        models.PositiveBigIntegerField(blank=True, null=True)
    )
    controller_ee_id: models.PositiveBigIntegerField = (
        models.PositiveBigIntegerField(null=True, blank=True)
    )
    credentials: models.JSONField = models.JSONField()
    executors: models.JSONField = models.JSONField(null=True, blank=True)

    pattern: models.ForeignKey = models.ForeignKey(
        Pattern, on_delete=models.CASCADE, related_name="pattern_instances"
    )
    controller_labels: models.ManyToManyField = models.ManyToManyField(
        ControllerLabel, related_name="pattern_instances", blank=True
    )


class Automation(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]

    automation_type_choices = (("job_template", "Job template"),)
    automation_type: models.CharField = models.CharField(
        max_length=200, choices=automation_type_choices
    )
    automation_id: models.PositiveBigIntegerField = (
        models.PositiveBigIntegerField()
    )
    primary: models.BooleanField = models.BooleanField(default=False)

    pattern_instance: models.ForeignKey = models.ForeignKey(
        PatternInstance, on_delete=models.CASCADE, related_name="automations"
    )


class Task(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]

    status_choices = (
        ("Initiated", "Initiated"),
        ("Running", "Running"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    )

    status: models.CharField = models.CharField(
        max_length=20, choices=status_choices
    )
    details: models.JSONField = models.JSONField(null=True, blank=True)


class ResourceState(models.Model):

    class Meta:
        app_label = "core"
        ordering = ["id"]

    class StateOptions(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        FAILED = "failed"
        COMPLETED = "completed"

    name: models.CharField = models.CharField(max_length=100)
    details: models.TextField = models.TextField()
    state: models.TextField = models.TextField(
        choices=StateOptions.choices, default=StateOptions.PENDING, null=False
    )
    task_id: models.UUIDField = models.UUIDField(null=True, default=None)
