import json
import os
import shutil
import tempfile
from typing import List
from unittest.mock import call
from unittest.mock import mock_open
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APITestCase

from core.models import Automation
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.services import pattern_instance_task
from core.services import pattern_task


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

        cls.automation = Automation.objects.create(
            automation_type="job_template",
            automation_id=789,
            primary=True,
            pattern_instance=cls.pattern_instance,
        )

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


class PatternTaskTest(SharedDataMixin, APITestCase):
    @patch("core.services.update_task_status", wraps=pattern_task.__globals__["update_task_status"])
    @patch("core.services.open", new_callable=mock_open, read_data='{"name": "test"}')
    @patch("core.services.download_collection")
    def test_run_pattern_task_success(self, mock_download, mock_open_fn, mock_update_status):
        pattern = Pattern.objects.create(
            collection_name="demo.collection",
            collection_version="1.0.0",
            pattern_name="test_pattern",
        )
        task = Task.objects.create(status="Initiated", details={})
        temp_dir = tempfile.mkdtemp()
        mock_download.return_value.__enter__.return_value = temp_dir

        os.makedirs(os.path.join(temp_dir, "extensions", "patterns", "test_pattern", "meta"))
        with open(os.path.join(temp_dir, "extensions", "patterns", "test_pattern", "meta", "pattern.json"), "w") as f:
            f.write(json.dumps({"name": "test"}))

        pattern_task(pattern.id, task.id)

        mock_update_status.assert_any_call(task, "Running", {"info": "Processing pattern"})
        mock_update_status.assert_any_call(task, "Completed", {"info": "Pattern processed successfully"})

    @patch("core.services.update_task_status", wraps=pattern_task.__globals__["update_task_status"])
    @patch("core.services.download_collection", side_effect=FileNotFoundError)
    def test_run_pattern_task_file_not_found(self, mock_download, mock_update_status):
        pattern = Pattern.objects.create(
            collection_name="demo.collection",
            collection_version="1.0.0",
            pattern_name="missing_pattern",
        )
        task = Task.objects.create(status="Initiated", details={})

        pattern_task(pattern.id, task.id)

        mock_update_status.assert_called_with(task, "Failed", {"error": "Pattern definition not found."})

    @patch("core.services.download_collection", side_effect=Exception("Download failed"))
    def test_run_pattern_task_handles_download_failure(self, mock_download):
        pattern_task(self.pattern.id, self.task.id)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Failed")
        self.assertIn("Download failed", self.task.details.get("error", ""))

    @patch("core.services.update_task_status", wraps=pattern_task.__globals__["update_task_status"])
    @patch("core.services.download_collection")
    def test_full_status_update_flow(self, mock_download, mock_update_status):
        temp_dir_path = self.create_temp_collection_dir()
        mock_download.return_value.__enter__.return_value = temp_dir_path

        # Run the task
        pattern_task(self.pattern.id, self.task.id)

        # Verify calls to update_task_status
        expected_calls = [
            (self.task, "Running", {"info": "Processing pattern"}),
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


class PatternInstanceTaskTest(SharedDataMixin, TestCase):
    @patch("core.services.assign_execute_roles")
    @patch("core.services.save_instance_state")
    @patch("core.services.create_job_templates")
    @patch("core.services.create_labels")
    @patch("core.services.create_execution_environment")
    @patch("core.services.create_project")
    @patch("core.services.update_task_status")
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

        pattern_instance_task(
            instance_id=self.pattern_instance.id,
            task_id=self.task.id,
        )

        mock_create_project.assert_called_once_with(self.pattern_instance, self.pattern, self.pattern.pattern_definition)
        mock_assign_roles.assert_called_once()

        # Ensure task marked Completed
        mock_update_status.assert_has_calls(
            [
                call(self.task, "Running", {"info": "Creating controller project"}),
                call(self.task, "Running", {"info": "Creating execution environment"}),
                call(self.task, "Running", {"info": "Creating labels"}),
                call(self.task, "Running", {"info": "Creating job templates"}),
                call(self.task, "Running", {"info": "Saving instance"}),
                call(self.task, "Running", {"info": "Assigning roles"}),
                call(self.task, "Completed", {"info": "PatternInstance processed"}),
            ]
        )

    @patch("core.services.assign_execute_roles")
    @patch("core.services.save_instance_state")
    @patch("core.services.create_job_templates")
    @patch("core.services.create_labels")
    @patch("core.services.create_execution_environment")
    @patch("core.services.create_project")
    @patch("core.services.update_task_status")
    def test_failure_path(
        self,
        mock_update_status,
        mock_create_project,
        *_,
    ):
        # Simulate failure inside create_project
        mock_create_project.side_effect = RuntimeError("error")

        # No exception should propagate because the task function swallows it
        pattern_instance_task(
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
