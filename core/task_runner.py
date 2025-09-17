import json
import logging
import os
from contextlib import closing

from core.utils.controller import assign_execute_roles
from core.utils.controller import build_collection_uri
from core.utils.controller import create_execution_environment
from core.utils.controller import create_job_templates
from core.utils.controller import create_labels
from core.utils.controller import create_project
from core.utils.controller import download_collection
from core.utils.controller import get_http_session
from core.utils.controller import save_instance_state

from .models import Pattern
from .models import PatternInstance
from .models import Task

logger = logging.getLogger(__name__)


def run_pattern_task(pattern_id: int, task_id: int) -> None:
    """
    Orchestrates downloading a collection and saving a pattern definition.

    Args:
        pattern_id (int): The ID of the pattern to process.
        task_id (int): The ID of the task.

    Raises:
        FileNotFoundError: If the pattern definition is not found.
        Exception: If any other error occurs.
    """
    task = Task.objects.get(id=task_id)
    task.mark_initiated({"info": "Processing started"})
    try:
        pattern = Pattern.objects.get(id=pattern_id)
        task.mark_running({"info": "Processing pattern"})
        with download_collection(
            pattern.collection_name, pattern.collection_version
        ) as collection_path:
            path_to_definition = os.path.join(
                collection_path,
                "extensions",
                "patterns",
                pattern.pattern_name,
                "meta",
                "pattern.json",
            )
            with open(path_to_definition, "r") as file:
                definition = json.load(file)

            pattern.pattern_definition = definition
            pattern.collection_version_uri = build_collection_uri(
                pattern.collection_name, pattern.collection_version
            )
            pattern.save(update_fields=["pattern_definition", "collection_version_uri"])
        task.mark_completed({"info": "Pattern processed successfully"})
    except FileNotFoundError:
        logger.error(f"Could not find pattern definition for task {task_id}")
        task.mark_failed({"error": "Pattern definition not found."})
    except Exception as e:
        error_message = f"An unexpected error occurred {str(e)}."
        logger.exception(f"Task {task_id} failed unexpectedly.")
        task.mark_failed({"error": error_message})


def run_pattern_instance_task(instance_id: int, task_id: int) -> None:
    task = Task.objects.get(id=task_id)
    try:
        instance = PatternInstance.objects.select_related("pattern").get(id=instance_id)
        pattern = instance.pattern
        pattern_def = pattern.pattern_definition

        if not pattern_def:
            raise ValueError("Pattern definition is missing.")

        # Create a single session for all AAP calls
        with closing(get_http_session()) as session:
            task.mark_running({"info": "Creating controller project"})
            project_id = create_project(session, instance, pattern)
            task.mark_running({"info": "Creating execution environment"})
            ee_id = create_execution_environment(session, instance, pattern_def)
            task.mark_running({"info": "Creating labels"})
            labels = create_labels(session, instance, pattern_def)
            task.mark_running({"info": "Creating job templates"})
            automations = create_job_templates(
                session, instance, pattern_def, project_id, ee_id
            )
            task.mark_running({"info": "Saving instance"})
            save_instance_state(instance, project_id, ee_id, labels, automations)
            task.mark_running({"info": "Assigning roles"})
            assign_execute_roles(session, instance.executors, automations)
            task.mark_completed({"info": "PatternInstance processed"})
    except Exception as e:
        logger.exception("Failed to process PatternInstance.")
        task.mark_failed({"error": str(e)})
