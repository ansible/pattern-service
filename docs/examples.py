from drf_spectacular.utils import OpenApiExample

automation_response = OpenApiExample(
    "Sample automation response",
    value={
        "id": 1,
        "url": "/api/pattern-service/v1/automations/1/",
        "related": {"pattern_instance": "/api/pattern-service/v1/pattern_instances/1/"},
        "summary_fields": {"pattern_instance": {"id": 1}},
        "created": "2025-06-25T01:02:03Z",
        "created_by": None,
        "modified": "2025-06-25T01:02:03Z",
        "modified_by": None,
        "automation_type": "job_template",
        "automation_id": 12,
        "primary": True,
        "pattern_instance": 1,
    },
    response_only=True,
)

controller_label_response = OpenApiExample(
    "Sample controller label response",
    value={
        "id": 1,
        "url": "/api/pattern-service/v1/controller_labels/1/",
        "related": {},
        "summary_fields": {},
        "created": "2025-06-25T01:02:03Z",
        "created_by": None,
        "modified": "2025-06-25T01:02:03Z",
        "modified_by": None,
        "label_id": 5,
    },
    response_only=True,
)

pattern_post = OpenApiExample(
    "Sample pattern POST",
    value={
        "collection_name": "mynamespace.mycollection",
        "collection_version": "1.0.0",
        "pattern_name": "mypattern",
    },
    request_only=True,
)

pattern_response = OpenApiExample(
    "Sample pattern response",
    value={
        "id": 1,
        "url": "/api/pattern-service/v1/patterns/1/",
        "related": {},
        "summary_fields": {},
        "created": "2025-06-25T01:02:03Z",
        "created_by": None,
        "modified": "2025-06-25T01:02:03Z",
        "modified_by": None,
        "collection_name": "mynamespace.mycollection",
        "collection_version": "1.0.0",
        "collection_version_uri": None,
        "pattern_name": "mypattern",
        "pattern_definition": None,
    },
    response_only=True,
)

pattern_instance_post = OpenApiExample(
    "Sample pattern instance POST",
    value={
        "organization_id": 1,
        "credentials": {
            "ee": 1,
            "project": 2,
        },
        "executors": {
            "teams": [1, 2],
            "users": [1, 2, 3],
        },
        "pattern": 1,
    },
    request_only=True,
)

pattern_instance_response = OpenApiExample(
    "Sample pattern instance response",
    value={
        "id": 1,
        "url": "/api/pattern-service/v1/pattern_instances/1/",
        "related": {"pattern": "/api/pattern-service/v1/patterns/1/"},
        "summary_fields": {"pattern": {"id": 1}},
        "created": "2025-06-25T01:02:03Z",
        "created_by": None,
        "modified": "2025-06-25T01:02:03Z",
        "modified_by": None,
        "organization_id": 1,
        "controller_project_id": None,
        "controller_ee_id": None,
        "controller_labels": [],
        "credentials": {"ee": 1, "project": 2},
        "executors": {
            "teams": [1, 2],
            "users": [1, 2, 3],
        },
        "pattern": 1,
    },
    response_only=True,
)
