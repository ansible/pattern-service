import json
import os
import shutil
import tempfile
from typing import List
from unittest.mock import patch

from django.test import TestCase

from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.task_runner import run_pattern_task


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
                "key": "value",
                "execution_environment_id": 10,
                "executors": ["exec1"],
                "controller_labels": [5],
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
        pattern_dir = os.path.join(
            collection_path, "extensions", "patterns", "example_pattern", "meta"
        )
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


class PatternTaskTest(SharedDataMixin, TestCase):
    @patch("core.models.Task.set_status", autospec=True, wraps=Task.set_status)
    @patch("core.task_runner.download_collection")
    def test_run_pattern_task_success(self, mock_download, mock_update_status):
        temp_dir_path = self.create_temp_collection_dir()
        mock_download.return_value.__enter__.return_value = temp_dir_path

        run_pattern_task(self.pattern.id, self.task.id)

        expected_calls = [
            (self.task, "Running", {"info": "Processing pattern"}),
            (self.task, "Completed", {"info": "Pattern processed successfully"}),
        ]

        actual_calls = [
            (call_args[0][0], call_args[0][1], call_args[0][2])
            for call_args in mock_update_status.call_args_list
        ]

        # Assert update_task_status calls
        for expected in expected_calls:
            self.assertIn(expected, actual_calls)

        # Assert final DB state
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Completed")
        self.assertEqual(
            self.task.details.get("info"), "Pattern processed successfully"
        )

        # Assert pattern definition was updated
        self.pattern.refresh_from_db()
        self.assertEqual(self.pattern.pattern_definition, {"mock_key": "mock_value"})

    @patch("core.models.Task.set_status", autospec=True)
    @patch("core.task_runner.download_collection", side_effect=FileNotFoundError)
    def test_run_pattern_task_file_not_found(self, mock_download, mock_update_status):
        pattern = Pattern.objects.create(
            collection_name="demo.collection",
            collection_version="1.0.0",
            pattern_name="missing_pattern",
        )
        task = Task.objects.create(status="Initiated", details={})

        run_pattern_task(pattern.id, task.id)

        mock_update_status.assert_called_with(
            task, "Failed", {"error": "Pattern definition not found."}
        )

    @patch(
        "core.task_runner.download_collection", side_effect=Exception("Download failed")
    )
    def test_run_pattern_task_handles_download_failure(self, mock_download):
        run_pattern_task(self.pattern.id, self.task.id)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Failed")
        self.assertIn("Download failed", self.task.details.get("error", ""))
