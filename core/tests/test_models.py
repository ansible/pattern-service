from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

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
        cls.label = ControllerLabel.objects.create(label_id=5)

    def create_pattern_instance(cls, org_id, **kwargs):
        defaults = {
            'controller_project_id': 10,
            'controller_ee_id': 20,
            'credentials': {"user": "admin"},
            'executors': [],
            'pattern': cls.pattern,
        }
        defaults.update(kwargs)
        return PatternInstance.objects.create(organization_id=org_id, **defaults)

    def create_automation(cls, pattern_instance, **kwargs):
        defaults = {
            'automation_type': "job_template",
            'automation_id': 12345,
            'primary': False,
        }
        defaults.update(kwargs)
        return Automation.objects.create(pattern_instance=pattern_instance, **defaults)


class PatternModelTestCase(SharedDataMixin, TestCase):
    def test_pattern_unique_info_constraint(self):
        """Test that patterns with same collection_name, collection_version, and pattern_name cannot be created"""
        with self.assertRaises(IntegrityError):
            Pattern.objects.create(
                collection_name="mynamespace.mycollection",
                collection_version="1.0.0",
                pattern_name="example_pattern",
                pattern_definition={"different": "value"},
            )

    def test_pattern_character_length_limits(self):
        with self.assertRaises(ValidationError):
            pattern = Pattern(collection_name="a" * 201, collection_version="1.0.0", pattern_name="test_pattern", pattern_definition={})
            pattern.full_clean()

        with self.assertRaises(ValidationError):
            pattern = Pattern(collection_name="test.collection", collection_version="a" * 51, pattern_name="test_pattern", pattern_definition={})
            pattern.full_clean()

        with self.assertRaises(ValidationError):
            pattern = Pattern(collection_name="test.collection", collection_version="1.0.0", pattern_name="a" * 201, pattern_definition={})
            pattern.full_clean()

        with self.assertRaises(ValidationError):
            pattern = Pattern(
                collection_name="test.collection",
                collection_version="1.0.0",
                pattern_name="test_pattern",
                collection_version_uri="a" * 201,
                pattern_definition={},
            )
            pattern.full_clean()


class PatternControllerLabelModelTestCase(SharedDataMixin, TestCase):
    def test_controller_label_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            ControllerLabel.objects.create(label_id=5)


class PatternInstanceModelTestCase(SharedDataMixin, TestCase):
    def test_create_pattern_instance(self):
        instance = self.create_pattern_instance(org_id=1, executors=[{"type": "podman"}])
        instance.controller_labels.add(self.label)
        self.assertEqual(instance.pattern, self.pattern)
        self.assertEqual(instance.organization_id, 1)
        self.assertEqual(instance.credentials["user"], "admin")
        self.assertIn(self.label, instance.controller_labels.all())

    def test_cascade_delete_pattern_to_instances(self):
        instance = self.create_pattern_instance(org_id=3, controller_project_id=30, controller_ee_id=40, credentials={"token": "xyz"})

        # Verify instance exists
        self.assertTrue(PatternInstance.objects.filter(id=instance.id).exists())

        # Delete the pattern
        self.pattern.delete()

        # Verify instance was cascade deleted
        self.assertFalse(PatternInstance.objects.filter(id=instance.id).exists())

    def test_pattern_unique_org_id_constraint(self):
        self.create_pattern_instance(org_id=1, controller_project_id=100, controller_ee_id=200, credentials={"token": "abc"})
        with self.assertRaises(IntegrityError):
            self.create_pattern_instance(org_id=1, controller_project_id=101, controller_ee_id=201, credentials={"token": "def"})

    def test_pattern_instance_null_fields(self):
        """Test creating pattern instance with null/optional fields"""
        instance = self.create_pattern_instance(
            org_id=5, controller_project_id=None, controller_ee_id=None, executors=None  # This can be null  # This can be null  # This can be null
        )

        self.assertIsNone(instance.controller_project_id)
        self.assertIsNone(instance.controller_ee_id)
        self.assertIsNone(instance.executors)
        self.assertEqual(instance.credentials["user"], "admin")

    def test_pattern_instance_required_fields(self):
        """Test that required fields cannot be null"""
        with self.assertRaises(IntegrityError):
            PatternInstance.objects.create(
                organization_id=None,
                credentials={"user": "admin"},
                pattern=self.pattern,
            )


class PatternAutomationModelTestCase(SharedDataMixin, TestCase):
    def test_cascade_delete_instance_to_automations(self):
        instance = self.create_pattern_instance(org_id=4, controller_project_id=50, controller_ee_id=60, credentials={"token": "xyz"})

        automation = self.create_automation(pattern_instance=instance, automation_id=99999, primary=True)

        # Verify automation exists
        self.assertTrue(Automation.objects.filter(id=automation.id).exists())

        # Delete the pattern instance
        instance.delete()

        # Verify automation was cascade deleted
        self.assertFalse(Automation.objects.filter(id=automation.id).exists())

    def test_automation_character_length_limits(self):
        instance = self.create_pattern_instance(org_id=6)

        with self.assertRaises(ValidationError):
            automation = Automation(
                automation_type="a" * 201,
                automation_id=12345,
                pattern_instance=instance,
            )
            automation.full_clean()

    def test_create_automation(self):
        instance = self.create_pattern_instance(org_id=2, controller_project_id=99, controller_ee_id=98, credentials={}, executors=[])
        automation = self.create_automation(pattern_instance=instance, primary=True)
        self.assertEqual(automation.automation_type, "job_template")
        self.assertTrue(automation.primary)

    def test_automation_invalid_type_choice(self):
        instance = self.create_pattern_instance(org_id=7)

        automation = Automation(
            automation_type="invalid_type",
            automation_id=12345,
            pattern_instance=instance,
        )
        with self.assertRaises(ValidationError):
            automation.full_clean()

    def test_automation_default_values(self):
        """Test that Automation model has correct default values"""
        instance = self.create_pattern_instance(org_id=8)

        automation = self.create_automation(
            pattern_instance=instance
            # Not setting primary, should default to False
        )
        self.assertFalse(automation.primary)


class PatternTaskModelTestCase(SharedDataMixin, TestCase):
    def test_task_character_length_limits(self):
        """Test max character length validation for Task fields"""
        with self.assertRaises(ValidationError):
            task = Task(status="a" * 21, details={})
            task.full_clean()

    def test_task_all_valid_status_choices(self):
        """Test all valid status choices for Task; covers both with and without details"""
        valid_statuses = ["Initiated", "Running", "Completed", "Failed"]
        for status in valid_statuses:
            task_with_details = Task.objects.create(status=status, details={"test": "data"})
            self.assertEqual(task_with_details.status, status)
            task_with_details.delete()

            task_with_empty_details = Task.objects.create(status=status, details={})
            self.assertEqual(task_with_empty_details.status, status)
            self.assertEqual(task_with_empty_details.details, {})
            task_with_empty_details.delete()

    def test_task_invalid_status_choice(self):
        task = Task(status="Unknown", details={})
        with self.assertRaises(ValidationError):
            task.full_clean()  # triggers choice validation
