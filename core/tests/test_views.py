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

        cls.task = Task.objects.create(status="Running", details={"progress": "50%"})


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

        # Task id returned directly
        task_id = response.data.get("task_id")
        self.assertIsInstance(task_id, int)

        # Task exists
        task = Task.objects.get(id=task_id)
        self.assertEqual(task.status, "Initiated")
        self.assertEqual(task.details.get("model"), "Pattern")
        self.assertEqual(task.details.get("id"), pattern.id)


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
