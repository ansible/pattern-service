import pytest
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from core import models
from docs import examples


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-06-25 01:02:03"):
        yield


@pytest.fixture()
def client():
    client = APIClient()
    return client


@pytest.fixture
def automation(db, pattern_instance) -> models.Automation:
    automation = models.Automation.objects.create(
        automation_type=examples.automation_response.value["automation_type"],
        automation_id=examples.automation_response.value["automation_id"],
        pattern_instance=pattern_instance,
        primary=examples.automation_response.value["primary"],
    )
    return automation


@pytest.fixture
def controller_label(db) -> models.ControllerLabel:
    controller_label = models.ControllerLabel.objects.create(label_id=examples.controller_label_response.value["label_id"])
    return controller_label


@pytest.fixture
def pattern(db) -> models.Pattern:
    pattern = models.Pattern.objects.create(
        collection_name=examples.pattern_post.value["collection_name"],
        collection_version=examples.pattern_post.value["collection_version"],
        pattern_name=examples.pattern_post.value["pattern_name"],
    )
    return pattern


@pytest.fixture
def pattern_instance(db, pattern) -> models.PatternInstance:
    pattern_instance = models.PatternInstance.objects.create(
        credentials=examples.pattern_instance_post.value["credentials"],
        executors=examples.pattern_instance_post.value["executors"],
        organization_id=1,
        pattern=pattern,
    )
    return pattern_instance


def test_retrieve_automation_success(db, client, automation):
    url = f"/api/pattern-service/v1/automations/{automation.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == examples.automation_response.value


def test_list_automations_success(db, client, automation):
    url = "/api/pattern-service/v1/automations/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [examples.automation_response.value]


def test_retrieve_controller_label_success(db, client, controller_label):
    url = f"/api/pattern-service/v1/controller_labels/{controller_label.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == examples.controller_label_response.value


def test_list_controller_labels_success(db, client, controller_label):
    url = "/api/pattern-service/v1/controller_labels/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [examples.controller_label_response.value]


def test_create_pattern_success(db, client):
    url = "/api/pattern-service/v1/patterns/"
    data = examples.pattern_post.value
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == examples.pattern_response.value


def test_retrieve_pattern_success(db, client, pattern):
    url = f"/api/pattern-service/v1/patterns/{pattern.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == examples.pattern_response.value


def test_list_patterns_success(db, client, pattern):
    url = "/api/pattern-service/v1/patterns/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [examples.pattern_response.value]


def test_create_pattern_instance_success(db, client, pattern):
    url = "/api/pattern-service/v1/pattern_instances/"
    data = examples.pattern_instance_post.value
    data["pattern"] = pattern.pk
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == examples.pattern_instance_response.value


def test_retrieve_pattern_instance_success(db, client, pattern_instance):
    url = f"/api/pattern-service/v1/pattern_instances/{pattern_instance.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == examples.pattern_instance_response.value


def test_list_pattern_instances_success(db, client, pattern_instance):
    url = "/api/pattern-service/v1/pattern_instances/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [examples.pattern_instance_response.value]
