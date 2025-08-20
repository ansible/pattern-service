import pytest
from freezegun import freeze_time
from rest_framework import status

from core import api_examples


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-06-25 01:02:03"):
        yield


def test_retrieve_automation_success(client, automation):
    url = f"/api/pattern-service/v1/automations/{automation.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == api_examples.automation_get_response.value


def test_list_automations_success(client, automation):
    url = "/api/pattern-service/v1/automations/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [api_examples.automation_get_response.value]


def test_retrieve_controller_label_success(client, controller_label):
    url = f"/api/pattern-service/v1/controller_labels/{controller_label.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == api_examples.controller_label_get_response.value


def test_list_controller_labels_success(client, controller_label):
    url = "/api/pattern-service/v1/controller_labels/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [api_examples.controller_label_get_response.value]


def test_create_pattern_success(client, db):
    url = "/api/pattern-service/v1/patterns/"
    data = api_examples.pattern_post_request.value
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == api_examples.pattern_post_response.value


def test_retrieve_pattern_success(client, pattern):
    url = f"/api/pattern-service/v1/patterns/{pattern.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == api_examples.pattern_get_response.value


def test_list_patterns_success(client, pattern):
    url = "/api/pattern-service/v1/patterns/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [api_examples.pattern_get_response.value]


def test_create_pattern_instance_success(client, pattern):
    url = "/api/pattern-service/v1/pattern_instances/"
    data = api_examples.pattern_instance_post_request.value
    data["pattern"] = pattern.pk
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == api_examples.pattern_instance_post_response.value


def test_retrieve_pattern_instance_success(client, controller_label, pattern_instance):
    pattern_instance.controller_labels.add(controller_label)
    url = f"/api/pattern-service/v1/pattern_instances/{pattern_instance.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == api_examples.pattern_instance_get_response.value


def test_list_pattern_instances_success(client, controller_label, pattern_instance):
    pattern_instance.controller_labels.add(controller_label)
    url = "/api/pattern-service/v1/pattern_instances/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [api_examples.pattern_instance_get_response.value]


def test_retrieve_task_success(client, task):
    url = f"/api/pattern-service/v1/tasks/{task.pk}/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == api_examples.task_get_response.value


def test_list_tasks_success(client, task):
    url = "/api/pattern-service/v1/tasks/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [api_examples.task_get_response.value]
