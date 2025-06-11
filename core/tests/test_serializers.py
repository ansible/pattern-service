from django.test import TestCase
from core.models import Pattern, ControllerLabel, PatternInstance
from core.serializers import PatternSerializer, ControllerLabelSerializer, PatternInstanceSerializer


class PatternSerializerTest(TestCase):
    def setUp(self):
        self.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={"Test": "Value"},
        )

    def test_serializer_fields_present(self):
        serializer = PatternSerializer(instance=self.pattern)
        data = serializer.data

        self.assertIn('id', data)
        self.assertIn('collection_name', data)
        self.assertIn('collection_version', data)
        self.assertIn('collection_version_uri', data)
        self.assertIn('pattern_name', data)
        self.assertIn('pattern_definition', data)

        self.assertEqual(data['collection_name'], "mynamespace.mycollection")
        self.assertEqual(data['collection_version'], "1.0.0")
        self.assertEqual(data['collection_version_uri'], "https://example.com/mynamespace/mycollection/")
        self.assertEqual(data['pattern_name'], "example_pattern")
        self.assertEqual(data['pattern_definition'], {"Test": "Value"})

    def test_pattern_definition_read_only(self):
        input_data = {
            "collection_name": "test-namespace.test-collection",
            "collection_version": "1.0.0",
            "collection_version_uri": "https://example.com/test-namespace/test-collection/",
            "pattern_name": "example_pattern",
            "pattern_definition": {"Test": "Value"},
        }

        serializer = PatternSerializer(data=input_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('pattern_definition', serializer.validated_data)

    def test_serializer_validation_success(self):
        input_data = {
            "collection_name": "test-namespace.test-collection",
            "collection_version": "1.0.0",
            "collection_version_uri": "https://example.com/test-namespace/test-collection/",
            "pattern_name": "example_pattern",
            "pattern_definition": {"Test": "Value"},
        }
        serializer = PatternSerializer(data=input_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ControllerLabelSerializerTest(TestCase):
    def setUp(self):
        self.label = ControllerLabel.objects.create(label_id=123)

    def test_serializer_fields(self):
        serializer = ControllerLabelSerializer(instance=self.label)
        data = serializer.data

        self.assertIn('id', data)
        self.assertIn('label_id', data)
        self.assertEqual(data['label_id'], 123)

    def test_serializer_validation(self):
        serializer = ControllerLabelSerializer(data={'label_id': 321})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_label_id(self):
        serializer = ControllerLabelSerializer(data={'label_id': 5})
        self.assertTrue(serializer.is_valid())

    def test_invalid_label_id(self):
        serializer = ControllerLabelSerializer(data={'label_id': -5})
        self.assertFalse(serializer.is_valid())
        self.assertIn('label_id', serializer.errors)


class PatternInstanceSerializerTest(TestCase):
    def setUp(self):
        self.pattern = Pattern.objects.create(
            collection_name="mynamespace.mycollection",
            collection_version="1.0.0",
            collection_version_uri="https://example.com/mynamespace/mycollection/",
            pattern_name="example_pattern",
            pattern_definition={"Test": "Value"},
        )
        self.instance = PatternInstance.objects.create(
            organization_id=1,
            controller_project_id=123,
            controller_ee_id=987,
            credentials={"user": "admin"},
            executors=[{"executor_type": "local"}],
            pattern=self.pattern,
        )

    def test_serializer_fields(self):
        serializer = PatternInstanceSerializer(instance=self.instance)
        data = serializer.data

        self.assertIn('id', data)
        self.assertIn('organization_id', data)
        self.assertIn('controller_project_id', data)
        self.assertIn('controller_ee_id', data)
        self.assertIn('pattern', data)
        self.assertEqual(data['controller_project_id'], 123)
        self.assertEqual(data['controller_ee_id'], 987)

    def test_serializer_validation(self):
        input_data = {
            "organization_id": 22,
            "controller_project_id": 123,
            "controller_ee_id": 987,
            "credentials": '{"user": "admin"}',
            "executors": '[{"executor_type": "local"}]',
            "pattern": self.pattern.id,
        }
        serializer = PatternInstanceSerializer(data=input_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
