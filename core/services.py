import contextlib
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List

from django.db import transaction

from core.controller_client import assign_execute_roles, build_collection_uri
from core.controller_client import create_execution_environment
from core.controller_client import create_job_templates
from core.controller_client import create_labels
from core.controller_client import create_project
from core.controller_client import get
from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance
from core.models import Task
from core.serializers import PatternInstanceSerializer

logger = logging.getLogger(__name__)


def update_task_status(task: Task, status_: str, details: dict):
    """
    Updates the status and details of a Task object.
    """
    task.status = status_
    task.details = details
    task.save()


@contextlib.contextmanager
def download_collection(collection: str, version: str) -> Iterator[str]:
    """
    Downloads and extracts a collection tarball to a temporary directory.

    Args:
        collection: The name of the collection (e.g., 'my_namespace.my_collection').
        version: The version of the collection (e.g., '1.0.0').

    Yields:
        The path to the extracted collection files.
    """
    path = f"/api/galaxy/v3/plugin/ansible/content/published/collections/artifacts/{collection}-{version}.tar.gz"
    temp_base_dir = tempfile.mkdtemp()
    collection_path = os.path.join(temp_base_dir, f"{collection}-{version}")
    os.makedirs(collection_path, exist_ok=True)
    try:
        response = get(path)
        in_memory_tar = io.BytesIO(response.content)
        with tarfile.open(fileobj=in_memory_tar, mode="r|*") as tar:
            tar.extractall(path=collection_path, filter="data")
        yield collection_path
    finally:
        shutil.rmtree(temp_base_dir)


def save_instance_state(instance: PatternInstance, project_id: int, ee_id: int, labels: List[ControllerLabel], automations: List[Dict[str, Any]]) -> None:
    """
    Saves the instance and links labels and automations inside a DB transaction.
    Args:
        instance: The PatternInstance to update.
        project_id: Controller project ID.
        ee_id: Execution environment ID.
        labels: List of ControllerLabel objects.
        automations: List of job template metadata.
    """
    with transaction.atomic():
        serializer = PatternInstanceSerializer(
            instance,
            data={
                "controller_project_id": project_id,
                "controller_execution_environment_id": ee_id,
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        for label in labels:
            instance.controller_labels.add(label)
        for auto in automations:
            instance.automations.create(
                automation_type=auto["type"],
                automation_id=auto["id"],
                primary=auto["primary"],
            )


def pattern_task(pattern_id: int, task_id: int):
    """
    Orchestrates downloading a collection and saving a pattern definition.
    """
    task = Task.objects.get(id=task_id)

    try:
        pattern = Pattern.objects.get(id=pattern_id)
        update_task_status(task, "Running", {"info": "Processing pattern"})
        collection_name: str = pattern.collection_name.replace(".", "-")
        with download_collection(collection_name, pattern.collection_version) as collection_path:
            path_to_definition = os.path.join(collection_path, "extensions", "patterns", pattern.pattern_name, "meta", "pattern.json")
            with open(path_to_definition, "r") as file:
                definition = json.load(file)

            pattern.pattern_definition = definition
            pattern.collection_version_uri = build_collection_uri(collection_name, pattern.collection_version)
            pattern.save(update_fields=["pattern_definition", "collection_version_uri"])
        update_task_status(task, "Completed", {"info": "Pattern processed successfully"})
    except FileNotFoundError:
        logger.error(f"Could not find pattern definition for task {task_id}")
        update_task_status(task, "Failed", {"error": "Pattern definition not found."})
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        update_task_status(task, "Failed", {"error": str(e)})


def pattern_instance_task(instance_id: int, task_id: int):
    task = Task.objects.get(id=task_id)
    try:
        instance = PatternInstance.objects.select_related("pattern").get(id=instance_id)
        pattern = instance.pattern
        pattern_def = pattern.pattern_definition

        if not pattern_def:
            raise ValueError("Pattern definition is missing.")

        update_task_status(task, "Running", {"info": "Creating controller project"})
        project_id = create_project(instance, pattern, pattern_def)
        update_task_status(task, "Running", {"info": "Creating execution environment"})
        ee_id = create_execution_environment(instance, pattern_def)
        update_task_status(task, "Running", {"info": "Creating labels"})
        labels = create_labels(instance, pattern_def)
        update_task_status(task, "Running", {"info": "Creating job templates"})
        automations = create_job_templates(instance, pattern_def, project_id, ee_id)
        update_task_status(task, "Running", {"info": "Saving instance"})
        save_instance_state(instance, project_id, ee_id, labels, automations)
        update_task_status(task, "Running", {"info": "Assigning roles"})
        assign_execute_roles(instance.executors, automations)
        update_task_status(task, "Completed", {"info": "PatternInstance processed"})
    except Exception as e:
        logger.exception("Failed to process PatternInstance.")
        update_task_status(task, "Failed", {"error": str(e)})
