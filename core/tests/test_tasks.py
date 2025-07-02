from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TestCase

from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.tasks import run_pattern_task


class SharedDataMixin:
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


class TaskTests(SharedDataMixin, TestCase):

    def test_run_pattern_task_with_uri(self):

        async def mock_download_and_extract_tarball(url):
            raise Exception("Download failed")

        task = Task.objects.create(status="Initiated", details={"model": "Pattern", "id": self.pattern.id})

        async def _run_pattern_task():
            await run_pattern_task(self.pattern.id, task.id)

        with patch("core.tasks.download_and_extract_tarball", new=mock_download_and_extract_tarball):
            async_to_sync(_run_pattern_task)()

        task.refresh_from_db()
        self.assertEqual(task.status, "Failed")

    def test_run_pattern_task_without_uri(self):
        pattern = self.pattern
        pattern.collection_version_uri = ""
        pattern.save()

        task = Task.objects.create(status="Initiated", details={"model": "Pattern", "id": pattern.id})

        async def _run_pattern_task():
            await run_pattern_task(pattern.id, task.id)

        async_to_sync(_run_pattern_task)()

        task.refresh_from_db()
        self.assertEqual(task.status, "Completed")
        self.assertIn("Pattern saved without external definition", task.details.get("info", ""))
