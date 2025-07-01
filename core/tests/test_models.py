import pytest
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status, details",
    [
        ("Running", {"info": "in progress"}),
        ("Running", {}),
    ],
)
def test_task_status_choices_valid(status, details):
    task = Task.objects.create(status=status, details=details)
    assert task.status == status
    if "info" in details:
        assert task.details["info"] == "in progress"
