import json
import logging
import os

from core.utils.controller import build_collection_uri
from core.utils.controller import download_collection

from .models import Pattern
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
