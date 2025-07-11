import json
import os
import shutil
import tempfile
from typing import List
from unittest.mock import mock_open
from unittest.mock import patch

from django.test import TestCase

from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.tasks import run_pattern_task


class SharedDataMixin:
    temp_dirs: List[str] = []

    @classmethod
    def setUpTestData(cls):
        cls.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={"key": "value", "execution_environment_id": 10, "executors": ["exec1"], "controller_labels": [5]},
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


class TaskTests(SharedDataMixin, TestCase):

    def test_run_pattern_task_with_uri(self):
        pattern = self.pattern

        def mock_download_collectionl(url, collection, version):
            raise Exception("Download failed")

        task = Task.objects.create(status="Initiated", details={"model": "Pattern", "id": self.pattern.id})

        with patch("core.tasks.download_collection", new=mock_download_collectionl):
            run_pattern_task(pattern.id, task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "Failed")

    def test_run_pattern_task_without_uri(self):
        pattern = self.pattern
        pattern.collection_version_uri = ""
        pattern.save()

        task = Task.objects.create(status="Initiated", details={"model": "Pattern", "id": pattern.id})

        run_pattern_task(pattern.id, task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "Completed")
        self.assertIn("Pattern saved without external definition", task.details.get("info", ""))

    @patch("core.tasks.update_task_status", wraps=run_pattern_task.__globals__["update_task_status"])
    @patch("core.tasks.download_collection")
    @patch("builtins.open", new_callable=mock_open, read_data='{"mock_key": "mock_value"}')
    def test_full_status_update_flow(self, mock_open_file, mock_download, mock_update_status):
        # Mock the download_collection to return a fake path
        mock_download.return_value = self.create_temp_collection_dir()

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
