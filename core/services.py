import contextlib
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
from typing import Iterator

from .controller_client import build_collection_uri
from .controller_client import get
from .models import Pattern
from .models import Task

logger = logging.getLogger(__name__)


def update_task_status(task: Task, status_: str, details: dict):
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

        logger.info(f"Collection extracted to {collection_path}")
        yield collection_path  # Yield the path to the caller
    finally:
        shutil.rmtree(temp_base_dir)


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
