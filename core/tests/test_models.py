from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from core.models import Automation
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task


class ModelTestCase(TestCase):
    def setUp(self):
        self.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={"key": "value"},
        )
        self.label = ControllerLabel.objects.create(label_id=5)

    def test_create_pattern_instance(self):
        instance = PatternInstance.objects.create(
            organization_id=1,
            controller_project_id=10,
            controller_ee_id=20,
            credentials={"user": "admin"},
            executors=[{"type": "podman"}],
            pattern=self.pattern,
        )
        instance.controller_labels.add(self.label)
        self.assertEqual(instance.pattern, self.pattern)
        self.assertEqual(instance.organization_id, 1)
        self.assertEqual(instance.credentials["user"], "admin")
        self.assertIn(self.label, instance.controller_labels.all())

    def test_pattern_instance_unique_constraint(self):
        PatternInstance.objects.create(
            organization_id=1,
            controller_project_id=100,
            controller_ee_id=200,
            credentials={"token": "abc"},
            executors=[],
            pattern=self.pattern,
        )
        with self.assertRaises(IntegrityError):
            PatternInstance.objects.create(
                organization_id=1,  # duplicate org + pattern
                controller_project_id=101,
                controller_ee_id=201,
                credentials={"token": "def"},
                executors=[],
                pattern=self.pattern,
            )

    def test_create_automation(self):
        pattern_instance = PatternInstance.objects.create(
            organization_id=2,
            controller_project_id=99,
            controller_ee_id=98,
            credentials={},
            executors=[],
            pattern=self.pattern,
        )
        automation = Automation.objects.create(
            automation_type="job_template",
            automation_id=12345,
            primary=True,
            pattern_instance=pattern_instance,
        )
        self.assertEqual(automation.automation_type, "job_template")
        self.assertTrue(automation.primary)

    def test_task_status_choices_valid(self):
        task = Task.objects.create(status="Running", details={"info": "in progress"})
        self.assertEqual(task.status, "Running")
        self.assertEqual(task.details["info"], "in progress")

    def test_task_invalid_status_choice(self):
        task = Task(status="Unknown", details={})
        with self.assertRaises(ValidationError):
            task.full_clean()  # triggers choice validation
