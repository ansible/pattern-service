from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional

from ansible_base.lib.abstract_models import CommonModel
from django.db import models


class Pattern(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["collection_name", "collection_version", "pattern_name"],
                name="unique_pattern_collection_version",
            )
        ]

    collection_name: models.CharField = models.CharField(max_length=200)
    collection_version: models.CharField = models.CharField(max_length=50)
    collection_version_uri: models.CharField = models.CharField(
        max_length=200, blank=True, null=True
    )
    pattern_name: models.CharField = models.CharField(max_length=200)
    pattern_definition: models.JSONField = models.JSONField(blank=True, null=True)


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

    organization_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField()
    controller_project_id: models.PositiveBigIntegerField = (
        models.PositiveBigIntegerField(blank=True, null=True)
    )
    controller_ee_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField(
        null=True, blank=True
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
    automation_id: models.PositiveBigIntegerField = models.PositiveBigIntegerField()
    primary: models.BooleanField = models.BooleanField(default=False)

    pattern_instance: models.ForeignKey = models.ForeignKey(
        PatternInstance, on_delete=models.CASCADE, related_name="automations"
    )


class Task(CommonModel):
    class Meta:
        app_label = "core"
        ordering = ["id"]

    class Status(models.TextChoices):
        INITIATED = "Initiated"
        RUNNING = "Running"
        COMPLETED = "Completed"
        FAILED = "Failed"

    status: models.CharField = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True
    )
    details: models.JSONField = models.JSONField(null=True, blank=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def set_status(
        self,
        new_status: str,
        details: Optional[Dict[str, Any]] = None,
        save_immediately: bool = True,
    ) -> None:
        """
        Safely update the task's status and optional details.

        Args:
            new_status (str): The new status (must be one of Status.choices).
            details (dict, optional): Additional info about this status update.
            save_immediately (bool): If True, saves the instance to the database
                immediately.

        Raises:
            ValueError: If the provided status is invalid.
        """
        if new_status not in self.Status.values:
            raise ValueError(
                f"Invalid status '{new_status}'. Allowed values: {self.Status.values}"
            )

        self.status = new_status
        self.details = details or {}
        if save_immediately:
            self.save(update_fields=["status", "details", "updated_at"])

    def mark_initiated(self, details: Optional[Dict[str, Any]] = None) -> None:
        self.set_status(self.Status.INITIATED, details)

    def mark_running(self, details: Optional[Dict[str, Any]] = None) -> None:
        self.set_status(self.Status.RUNNING, details)

    def mark_completed(self, details: Optional[Dict[str, Any]] = None) -> None:
        self.set_status(self.Status.COMPLETED, details)

    def mark_failed(self, details: Optional[Dict[str, Any]] = None) -> None:
        self.set_status(self.Status.FAILED, details)

    def __str__(self) -> str:
        return f"Task #{self.pk} - {self.status}"
