from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import ControllerLabel
from core.models import Pattern
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

    def test_task_invalid_status_choice(self):
        task = Task(status="Unknown", details={})
        with self.assertRaises(ValidationError):
            task.full_clean()  # triggers choice validation

    def test_task_status_choices_valid_running_with_info(self):
        task = Task.objects.create(status="Running", details={"info": "in progress"})
        self.assertEqual(task.status, "Running")
        self.assertEqual(task.details["info"], "in progress")

    def test_task_status_choices_valid_running_empty_details(self):
        task = Task.objects.create(status="Running", details={})
        self.assertEqual(task.status, "Running")
        self.assertEqual(task.details, {})
