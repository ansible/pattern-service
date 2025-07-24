import json
import os
import shutil
import tempfile
from typing import List
from unittest.mock import mock_open
from unittest.mock import patch

from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.tasks import run_pattern_task
from core.tasks import run_pattern_instance_task


class SharedDataMixin:
    temp_dirs: List[str] = []

    @classmethod
    def setUpTestData(cls):
        cls.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={
                "schema_version": "1.0",
                "name": "demo_pattern",
                "title": "Create a demo resource",
                "description": "This pattern provisions a demo resource using AAP.",
                "short_description": "Provision demo resource",
                "aap_resources": {
                    "controller_project": {"name": "Demo Project", "description": "A demo project for testing"},
                    "controller_job_templates": [{"name": "Run demo job", "description": "Runs the demo automation", "playbook": "main.yml"}],
                },
            },
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

        cls.task = Task.objects.create(status="Running", details={"progress": "50%"})

    def register_temp_dir(self, path: str):
        self.temp_dirs.append(path)

    def create_temp_collection_dir(self) -> str:
        """
        Creates and tracks a temp collection directory with pattern.json.
        """
        temp_dir = tempfile.mkdtemp()
        self.register_temp_dir(temp_dir)

        collection_path = os.path.join(temp_dir, "mynamespace-mycollection-1.0.0")
        pattern_dir = os.path.join(collection_path, "extensions", "patterns", "example_pattern", "meta")
        os.makedirs(pattern_dir, exist_ok=True)

        with open(os.path.join(pattern_dir, "pattern.json"), "w") as f:
            json.dump({"mock_key": "mock_value"}, f)

        return collection_path

    def tearDown(self):
        """
        Automatically called after each test. Cleans up any temp dirs created.
        """
        for temp_dir in getattr(self, "temp_dirs", []):
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()


class PatternInstanceViewSetTest(SharedDataMixin, APITestCase):
    # ---------------------------------------------------------------------------
    # run_pattern_instance_task(): success case
    # ---------------------------------------------------------------------------

    @patch("core.tasks.assign_execute_roles")
    @patch("core.tasks.save_instance_state")
    @patch("core.tasks.create_job_templates")
    @patch("core.tasks.create_labels")
    @patch("core.tasks.create_execution_environment")
    @patch("core.tasks.create_controller_project")
    @patch("core.tasks.update_task_status")
    def test_run_pattern_instance_success(
        self,
        mock_update_status,
        mock_create_project,
        mock_create_ee,
        mock_create_labels,
        mock_create_jts,
        mock_save_instance,
        mock_assign_roles,
    ):
        mock_create_project.side_effect = [321]
        mock_create_ee.side_effect = [654]
        mock_create_labels.side_effect = [[]]
        mock_create_jts.side_effect = [[]]

        run_pattern_instance_task(
            instance_id=self.pattern_instance.id,
            task_id=self.task.id,
        )

        mock_create_project.assert_called_once_with(self.pattern_instance, self.pattern, self.pattern.pattern_definition)
        mock_assign_roles.assert_called_once()

        # Ensure task marked Completed
        mock_update_status.assert_any_call(self.task, "Completed", {"info": "PatternInstance processed"})

    # ---------------------------------------------------------------------------
    # run_pattern_instance_task(): failure case
    # ---------------------------------------------------------------------------

    @patch("core.tasks.assign_execute_roles")
    @patch("core.tasks.save_instance_state")
    @patch("core.tasks.create_job_templates")
    @patch("core.tasks.create_labels")
    @patch("core.tasks.create_execution_environment")
    @patch("core.tasks.create_controller_project")
    @patch("core.tasks.update_task_status")
    def test_failure_path(
        self,
        mock_update_status,
        mock_create_project,
        *_,
    ):
        # Simulate failure inside create_controller_project
        mock_create_project.side_effect = RuntimeError("error")

        # No exception should propagate because the task function swallows it
        run_pattern_instance_task(
            instance_id=self.pattern_instance.id,
            task_id=self.task.id,
        )

        # Verify that the task was marked Failed with the right message
        mock_update_status.assert_any_call(
            self.task,
            "Failed",
            {"error": "error"},
        )

        mock_create_project.assert_called_once()


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
        self.assertIn('id', response.data)
        self.assertIn('label_id', response.data)
        self.assertEqual(response.data['label_id'], 5)
        self.task = Task.objects.create(status="Running", details={"progress": "50%"})


class TaskTests(SharedDataMixin, APITestCase):

    def test_run_pattern_task_handles_download_failure(self):
        pattern = self.pattern

        task = Task.objects.create(status="Initiated", details={"model": "Pattern", "id": self.pattern.id})

        with patch("core.tasks.download_collection", side_effect=Exception("Download failed")):
            run_pattern_task(pattern.id, task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "Failed")
        self.assertIn("Download failed", task.details.get("error", ""))

    @patch("core.tasks.update_task_status", wraps=run_pattern_task.__globals__["update_task_status"])
    @patch("core.tasks.download_collection")
    def test_full_status_update_flow(self, mock_download, mock_update_status):
        temp_dir_path = self.create_temp_collection_dir()
        mock_download.return_value.__enter__.return_value = temp_dir_path

        # Run the task
        run_pattern_task(self.pattern.id, self.task.id)

        # Verify calls to update_task_status
        expected_calls = [
            (self.task, "Running", {"info": "Processing pattern"}),
            (self.task, "Running", {"info": "Downloading collection tarball"}),
            (self.task, "Completed", {"info": "Pattern processed successfully"}),
        ]
        actual_calls = [tuple(call.args) for call in mock_update_status.call_args_list]
        for expected in expected_calls:
            self.assertIn(expected, actual_calls)

        # Verify final DB state
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Completed")
        self.assertEqual(self.task.details.get("info"), "Pattern processed successfully")

        # Verify pattern_definition was updated and saved
        self.pattern.refresh_from_db()
        self.assertEqual(self.pattern.pattern_definition, {"mock_key": "mock_value"})
