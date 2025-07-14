import contextlib
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
from typing import Iterator

import requests

from .models import Pattern
from .models import Task

logger = logging.getLogger(__name__)


def update_task_status(task: Task, status_: str, details: dict):
    task.status = status_
    task.details = details
    task.save()


@contextlib.contextmanager
def download_collection(url: str, collection: str, version: str) -> Iterator[str]:
    """
    Downloads and extracts a collection to a temporary path.
    Returns the path where files were extracted.
    """
    temp_base_dir = tempfile.mkdtemp()

    collection_path = os.path.join(temp_base_dir, f"{collection}-{version}")
    os.makedirs(collection_path, exist_ok=True)

    try:
        response = requests.get(url)
        response.raise_for_status()
        in_memory_tar = io.BytesIO(response.content)

        with tarfile.open(fileobj=in_memory_tar, mode="r|*") as tar:
            tar.extractall(path=collection_path, filter="data")

        logger.info(f"Collection extracted to {collection_path}")
        yield collection_path  # Yield the path to the caller
    finally:
        shutil.rmtree(temp_base_dir)


def run_pattern_task(pattern_id: int, task_id: int):
    """
    Orchestrates downloading a collection and saving a pattern definition.
    """
    task = Task.objects.get(id=task_id)

    try:
        pattern = Pattern.objects.get(id=pattern_id)
        update_task_status(task, "Running", {"info": "Processing pattern"})

        # Skip download if URI is missing
        if not pattern.collection_version_uri:
            update_task_status(task, "Completed", {"info": "Pattern saved without external definition"})
            return

        update_task_status(task, "Running", {"info": "Downloading collection tarball"})

        # Get all necessary names from the pattern object
        collection_name = pattern.collection_name.replace(".", "-")
        collection_version = pattern.collection_version
        pattern_name = pattern.pattern_name

        with download_collection(pattern.collection_version_uri, collection_name, collection_version) as collection_path:
            path_to_definition = os.path.join(collection_path, "extensions", "patterns", pattern_name, "meta", "pattern.json")

            with open(path_to_definition, "r") as file:
                definition = json.load(file)

            pattern.pattern_definition = definition
            pattern.save()

        update_task_status(task, "Completed", {"info": "Pattern processed successfully"})

    except FileNotFoundError:
        logger.error(f"Could not find pattern definition for task {task_id}")
        update_task_status(task, "Failed", {"error": "Pattern definition file not found in collection."})

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        update_task_status(task, "Failed", {"error": str(e)})
