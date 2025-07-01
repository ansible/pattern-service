import json
import os
import tarfile
import tempfile

import aiohttp
from asgiref.sync import sync_to_async
from django.db import transaction

from .models import ControllerLabel
from .models import Pattern
from .models import PatternInstance
from .models import Task


async def update_task_status(task: Task, status_: str, details: dict):
    task.status = status_
    task.details = details
    await sync_to_async(task.save, thread_sensitive=True)()


async def download_and_extract_tarball(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download tarball: HTTP {resp.status}")

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(await resp.read())
                tmp_path = tmp.name

    extract_dir = tempfile.mkdtemp()
    with tarfile.open(tmp_path, 'r:*') as tar:
        tar.extractall(path=extract_dir)

    # Look for a .pattern.json or similar file
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            if fname.endswith(".json"):
                with open(os.path.join(root, fname)) as f:
                    return json.load(f)

    raise Exception("Pattern definition JSON file not found in tarball")


async def run_pattern_task(pattern_id: int, task_id: int):
    task = await sync_to_async(Task.objects.get, thread_sensitive=True)(id=task_id)

    try:
        pattern = await sync_to_async(Pattern.objects.get, thread_sensitive=True)(id=pattern_id)
        await update_task_status(task, "Running", {"info": "Processing pattern"})

        # Skip download if URI is missing
        if not pattern.collection_version_uri:
            await update_task_status(task, "Completed", {"info": "Pattern saved without external definition"})
            return

        await update_task_status(task, "Running", {"info": "Downloading collection tarball"})
        definition = await download_and_extract_tarball(pattern.collection_version_uri)
        pattern.pattern_definition = definition

        await sync_to_async(pattern.save, thread_sensitive=True)()

        await update_task_status(task, "Completed", {"info": "Pattern processed successfully"})
    except Exception as e:
        await update_task_status(task, "Failed", {"error": str(e)})


async def run_pattern_instance_task(instance_id: int, task_id: int):
    task = await sync_to_async(Task.objects.get, thread_sensitive=True)(id=task_id)

    try:
        instance = await sync_to_async(PatternInstance.objects.select_related("pattern").get, thread_sensitive=True)(id=instance_id)
        pattern = instance.pattern

        # Make sure the Pattern has pattern_definition loaded (could be empty)
        pattern_def = pattern.pattern_definition or {}

        await update_task_status(task, "Running", {"info": "Processing PatternInstance"})

        if not pattern_def:
            raise Exception("Pattern definition is missing. Cannot process instance.")

        # Update instance fields with data from pattern definition inside transaction
        def update_instance():
            with transaction.atomic():
                if "execution_environment_id" in pattern_def:
                    instance.controller_ee_id = int(pattern_def["execution_environment_id"])
                if "executors" in pattern_def:
                    instance.executors = pattern_def["executors"]
                if "controller_labels" in pattern_def:
                    for label_id in pattern_def["controller_labels"]:
                        label_obj, _ = ControllerLabel.objects.get_or_create(label_id=label_id)
                        instance.controller_labels.add(label_obj)

                instance.controller_project_id = hash(pattern.pattern_name) % 10**6
                instance.save()

        await sync_to_async(update_instance, thread_sensitive=True)()

        await update_task_status(task, "Completed", {"info": "PatternInstance processed"})
    except Exception as e:
        await update_task_status(task, "Failed", {"error": str(e)})
