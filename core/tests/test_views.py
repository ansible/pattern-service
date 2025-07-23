import json
import os
import shutil
import tempfile
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Automation
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task


class SharedDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={"key": "value"},
        )

        cls.pattern_instance = PatternInstance.objects.create(
            organization_id=1,
            controller_project_id=123,
            controller_ee_id=456,
            credentials={"user": "admin"},
            executors=[{"executor_type": "container"}],
            pattern=cls.pattern,
        )

        cls.label = ControllerLabel.objects.create(label_id=5)
        cls.pattern_instance.controller_labels.add(cls.label)

        cls.automation = Automation.objects.create(
            automation_type="job_template",
            automation_id=789,
            primary=True,
            pattern_instance=cls.pattern_instance,
        )

        cls.task1 = Task.objects.create(status="Running", details={"progress": "50%"})
        cls.task2 = Task.objects.create(
            status="Completed", details={"result": "success"}
        )
        cls.task3 = Task.objects.create(status="Failed", details={"error": "timeout"})


class PatternViewSetTest(SharedDataMixin, APITestCase):
    def test_pattern_list_view(self):
        url = reverse("pattern-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["pattern_name"], "example_pattern")

    def test_pattern_detail_view(self):
        url = reverse("pattern-detail", args=[self.pattern.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["collection_name"], "mynamespace.mycollection")

    def test_pattern_create_view(self):
        url = reverse("pattern-list")
        data = {
            "collection_name": "new.namespace.collection",
            "collection_version": "1.2.3",
            "collection_version_uri": "https://example.com/new.tar.gz",
            "pattern_name": "new_pattern",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Pattern created
        pattern = Pattern.objects.get(pattern_name="new_pattern")
        self.assertIsNotNone(pattern)

        # Task ID returned directly
        task_id = response.data.get("task_id")
        self.assertIsInstance(task_id, int)

        # Task exists
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, "Initiated")
        self.assertEqual(task.details.get("model"), "Pattern")
        self.assertEqual(task.details.get("id"), pattern.id)

    def test_pattern_delete_view(self):
        # Create a separate pattern for deletion
        pattern_to_delete = Pattern.objects.create(
            collection_name="delete.test",
            collection_version="1.0.0",
            pattern_name="deletable_pattern",
            pattern_definition={},
        )

        url = reverse("pattern-detail", args=[pattern_to_delete.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify database change - pattern should be deleted
        self.assertFalse(Pattern.objects.filter(pk=pattern_to_delete.pk).exists())

    def test_pattern_create_with_invalid_data(self):
        url = reverse("pattern-list")
        data = {"invalid_field": "invalid"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ControllerLabelViewSetTest(SharedDataMixin, APITestCase):
    def test_label_list_view(self):
        url = reverse("controllerlabel-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_label_detail_view(self):
        url = reverse("controllerlabel-detail", args=[self.label.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertIn("label_id", response.data)
        self.assertEqual(response.data["label_id"], 5)

    def test_label_create_view(self):
        url = reverse("controllerlabel-list")
        data = {"label_id": 10}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        label = ControllerLabel.objects.get(label_id=10)
        self.assertIsNotNone(label)
        self.assertEqual(label.label_id, 10)

    def test_label_delete_view(self):
        label_to_delete = ControllerLabel.objects.create(label_id=99)

        url = reverse("controllerlabel-detail", args=[label_to_delete.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify database change - label should be deleted
        self.assertFalse(ControllerLabel.objects.filter(pk=label_to_delete.pk).exists())


class PatternInstanceViewSetTest(SharedDataMixin, APITestCase):
    def test_pattern_instance_list_view(self):
        url = reverse("patterninstance-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_pattern_instance_detail_view(self):
        url = reverse("patterninstance-detail", args=[self.pattern_instance.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["organization_id"], 1)

    def test_pattern_instance_create_view(self):
        url = reverse("patterninstance-list")
        data = {
            "organization_id": 2,
            "controller_project_id": 0,
            "controller_ee_id": 0,
            "credentials": {"user": "tester"},
            "executors": [],
            "pattern": self.pattern.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # PatternInstance created - verify it exists
        instance = PatternInstance.objects.get(organization_id=2)
        self.assertIsNotNone(instance)
        # Verify the fields were saved correctly
        self.assertEqual(instance.organization_id, 2)
        self.assertEqual(instance.credentials["user"], "tester")

        # Task id returned directly
        task_id = response.data.get("task_id")
        self.assertIsInstance(task_id, int)

        # Task exists
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, "Initiated")
        self.assertEqual(task.details.get("model"), "PatternInstance")
        self.assertEqual(task.details.get("id"), instance.id)

    def test_pattern_instance_delete_view(self):
        # Create a separate instance for deletion
        instance_to_delete = PatternInstance.objects.create(
            organization_id=999,
            controller_project_id=111,
            controller_ee_id=222,
            credentials={"user": "deletable"},
            pattern=self.pattern,
        )

        url = reverse("patterninstance-detail", args=[instance_to_delete.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify database change - instance should be deleted
        self.assertFalse(
            PatternInstance.objects.filter(pk=instance_to_delete.pk).exists()
        )

    def test_pattern_instance_create_view_with_invalid_pattern(self):
        url = reverse("patterninstance-list")
        data = {
            "organization_id": 999,
            "credentials": {"user": "test"},
            "pattern": 99999,
        }  # Non-existent pattern ID

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AutomationViewSetTest(SharedDataMixin, APITestCase):
    def test_automation_list_view(self):
        url = reverse("automation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_automation_detail_view(self):
        url = reverse("automation-detail", args=[self.automation.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automation_type"], "job_template")

    def test_automation_create_view(self):
        url = reverse("automation-list")
        data = {
            "automation_type": "job_template",
            "automation_id": 1234,
            "primary": False,
            "pattern_instance": self.pattern_instance.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify database change
        automation = Automation.objects.get(automation_id=1234)
        self.assertIsNotNone(automation)
        self.assertEqual(automation.automation_type, "job_template")
        self.assertFalse(automation.primary)

    def test_automation_delete_view(self):
        # Create a separate automation for deletion
        automation_to_delete = Automation.objects.create(
            automation_type="job_template",
            automation_id=5555,
            primary=False,
            pattern_instance=self.pattern_instance,
        )

        url = reverse("automation-detail", args=[automation_to_delete.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify database change - automation should be deleted
        self.assertFalse(Automation.objects.filter(pk=automation_to_delete.pk).exists())

    def test_automation_create_view_with_invalid_pattern_instance(self):
        url = reverse("automation-list")
        data = {
            "automation_type": "job_template",
            "automation_id": 1234,
            "pattern_instance": 99999,
        }  # Non-existent pattern instance ID

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskViewSetTest(SharedDataMixin, APITestCase):
    def test_task_list_view(self):
        url = reverse("task-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_task_detail_view(self):
        url = reverse("task-detail", args=[self.task1.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertIn("status", response.data)
        self.assertIn("details", response.data)

    def test_task_list_view_returns_all_tasks(self):
        url = reverse("task-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we get all created tasks
        task_ids = [task["id"] for task in response.data]
        expected_ids = [self.task1.id, self.task2.id, self.task3.id]
        self.assertEqual(sorted(task_ids), sorted(expected_ids))

    def test_task_detail_view_for_different_statuses(self):
        tasks_to_test = [
            (self.task1, "Running"),
            (self.task2, "Completed"),
            (self.task3, "Failed"),
        ]

        for task, expected_status in tasks_to_test:
            with self.subTest(status=expected_status):
                url = reverse("task-detail", args=[task.pk])
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_task_detail_view_nonexistent_task(self):
        url = reverse("task-detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
<<<<<<< HEAD
=======


class PatternViewSetTest(SharedDataMixin, APITestCase):
    def create_temp_collection_dir(self):
        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "extensions", "patterns", "new_pattern", "meta"), exist_ok=True)
        pattern_json_path = os.path.join(temp_dir, "extensions", "patterns", "new_pattern", "meta", "pattern.json")
        with open(pattern_json_path, "w") as f:
            json.dump({"mock_key": "mock_value"}, f)
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return temp_dir

    def test_pattern_list_view(self):
        url = reverse("pattern-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["pattern_name"], "example_pattern")

    def test_pattern_detail_view(self):
        url = reverse("pattern-detail", args=[self.pattern.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["collection_name"], "mynamespace.mycollection")

    @patch("core.tasks.download_collection")
    def test_pattern_create_view(self, mock_download_collection):
        temp_dir = self.create_temp_collection_dir()  # Simulate a valid pattern.json
        mock_download_collection.return_value.__enter__.return_value = temp_dir

        url = reverse("pattern-list")
        data = {
            "collection_name": "newnamespace.collection",
            "collection_version": "1.2.3",
            "collection_version_uri": "https://example.com/new.tar.gz",
            "pattern_name": "new_pattern",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Pattern created
        pattern = Pattern.objects.get(pattern_name="new_pattern")
        self.assertIsNotNone(pattern)

        # Task id returned directly
        task_id = response.data.get("task_id")
        self.assertIsInstance(task_id, int)

        # Task exists
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, "Completed")
        self.assertEqual(task.details.get("info"), "Pattern processed successfully")


class PatternInstanceViewSetTest(SharedDataMixin, APITestCase):
    def test_pattern_instance_list_view(self):
        url = reverse("patterninstance-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_pattern_instance_detail_view(self):
        url = reverse("patterninstance-detail", args=[self.pattern_instance.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["organization_id"], 1)

    def test_pattern_instance_create_view(self):
        url = reverse("patterninstance-list")
        data = {
            "organization_id": 2,
            "controller_project_id": 0,
            "controller_ee_id": 0,
            "credentials": {"user": "tester"},
            "executors": [],
            "pattern": self.pattern.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        instance = PatternInstance.objects.get(organization_id=2)
        self.assertIsNotNone(instance)

        task_id = response.data.get("task_id")
        self.assertIsInstance(task_id, int)

        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, "Initiated")
        self.assertEqual(task.details.get("model"), "PatternInstance")
        self.assertEqual(task.details.get("id"), instance.id)
>>>>>>> fbc5163 (Update)
