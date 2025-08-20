import pytest
from rest_framework.test import APIClient

from core import api_examples
from core import models


@pytest.fixture()
def client():
    client = APIClient()
    return client


@pytest.fixture()
def automation(db, pattern_instance) -> models.Automation:
    automation = models.Automation.objects.create(
        automation_type=api_examples.automation_get_response.value["automation_type"],
        automation_id=api_examples.automation_get_response.value["automation_id"],
        pattern_instance=pattern_instance,
        primary=api_examples.automation_get_response.value["primary"],
    )
    return automation


@pytest.fixture()
def controller_label(db) -> models.ControllerLabel:
    controller_label = models.ControllerLabel.objects.create(
        label_id=api_examples.controller_label_get_response.value["label_id"]
    )
    return controller_label


@pytest.fixture()
def pattern(db) -> models.Pattern:
    pattern = models.Pattern.objects.create(
        collection_name=api_examples.pattern_post_request.value["collection_name"],
        collection_version=api_examples.pattern_post_request.value[
            "collection_version"
        ],
        pattern_name=api_examples.pattern_post_request.value["pattern_name"],
    )
    return pattern


@pytest.fixture()
def pattern_instance(db, pattern) -> models.PatternInstance:
    pattern_instance = models.PatternInstance.objects.create(
        credentials=api_examples.pattern_instance_post_request.value["credentials"],
        executors=api_examples.pattern_instance_post_request.value["executors"],
        organization_id=1,
        pattern=pattern,
    )
    return pattern_instance


@pytest.fixture()
def task(db) -> models.Task:
    task = models.Task.objects.create(
        status=api_examples.task_get_response.value["status"],
        details=api_examples.task_get_response.value["details"],
    )
    return task
