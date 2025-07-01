from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TestCase

from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.tasks import run_pattern_instance_task
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

    def test_run_pattern_instance_task_success(self):
        # Create task synchronously
        task = Task.objects.create(status="Initiated", details={"model": "PatternInstance", "id": self.pattern_instance.id})

        async def _run_pattern_instance_task():
            await run_pattern_instance_task(self.pattern_instance.id, task.id)

        # Run async part with async_to_sync
        async_to_sync(_run_pattern_instance_task)()

        # Fetch updated task
        task.refresh_from_db()
        self.assertEqual(task.status, "Completed")
        instance = PatternInstance.objects.get(id=self.pattern_instance.id)
        self.assertEqual(instance.controller_ee_id, 10)
        self.assertEqual(instance.executors, ["exec1"])
        self.assertTrue(instance.controller_labels.filter(label_id=5).exists())

    def test_run_pattern_instance_task_failure_missing_pattern_def(self):
        pattern = self.pattern
        pattern.pattern_definition = None
        pattern.save()

        # Create PatternInstance linked to this Pattern
        pattern_instance = PatternInstance.objects.create(
            organization_id=9999,
            pattern=pattern,
            credentials={},
            executors=None,
        )

        # Create the Task linked to the pattern_instance
        task = Task.objects.create(status="Initiated", details={"model": "PatternInstance", "id": pattern_instance.id})

        async def test():
            await run_pattern_instance_task(pattern_instance.id, task.id)

        async_to_sync(test)()

        task.refresh_from_db()

        self.assertEqual(task.status, "Failed")
        self.assertIn("pattern definition is missing", task.details.get("error").lower())
