from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Task


class SharedDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.task1 = Task.objects.create(status="Running", details={"progress": "50%"})
        cls.task2 = Task.objects.create(status="Completed", details={"result": "success"})
        cls.task3 = Task.objects.create(status="Failed", details={"error": "timeout"})


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
        self.assertIn('id', response.data)
        self.assertIn('status', response.data)
        self.assertIn('details', response.data)

    def test_task_list_view_returns_all_tasks(self):
        url = reverse("task-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we get all created tasks
        task_ids = [task['id'] for task in response.data]
        expected_ids = [self.task1.id, self.task2.id, self.task3.id]
        self.assertEqual(sorted(task_ids), sorted(expected_ids))

    def test_task_detail_view_for_different_statuses(self):
        tasks_to_test = [(self.task1, "Running"), (self.task2, "Completed"), (self.task3, "Failed")]

        for task, expected_status in tasks_to_test:
            with self.subTest(status=expected_status):
                url = reverse("task-detail", args=[task.pk])
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_task_detail_view_nonexistent_task(self):
        url = reverse("task-detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
