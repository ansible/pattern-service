import contextlib
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
from urllib.parse import urlparse
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence

import requests
from requests import Session
from requests.auth import HTTPBasicAuth

from pattern_service.settings.aap import get_aap_settings

from .models import Pattern
from .models import PatternInstance
from .models import ControllerLabel
from .models import Task

logger = logging.getLogger(__name__)

settings = get_aap_settings()
_aap_session: Optional[Session] = None


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


def get_http_session(force_refresh: bool = False) -> Session:
    """Returns a cached Session instance with AAP credentials."""
    global _aap_session
    if _aap_session is None or force_refresh:
        session = Session()
        session.auth = HTTPBasicAuth(settings.username, settings.password)
        session.verify = settings.verify_ssl
        session.headers.update({'Content-Type': 'application/json'})
        _aap_session = session

    return _aap_session


def post(
    path: str,
    data: Dict,
    *,
    dedupe_keys: Sequence[str] = ("name", "organization"),
) -> Dict:
    """
    Create a resource on the AAP controller.
    If the POST fails with 400 because the object already exists,
    perform a GET lookup using *dedupe_keys* taken from *data* and
    return the existing object instead.
    Args:
        path: Controller endpoint, e.g. "/projects/" (must include trailing slash).
        data: JSON payload to send.
        dedupe_keys: Keys from *data* to copy into the lookup query string when handling
            a duplicate‑name error.
    Returns:
        JSON for the created or pre‑existing object.
    Raises:
        requests.HTTPError
            Propagated if the status code is not a handled 400 or if the lookup
            returns no result.
    """
    session = get_http_session()
    url = f"{settings.url}{path}"

    try:
        response = session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code != 400:
            raise

        logger.debug(f"AAP POST {url} returned 400. Attempting dedup lookup with keys {str(dedupe_keys)}")

        # Build ?name=foo&organization=123 query if those keys exist in *data*
        params = {k: data[k] for k in dedupe_keys if k in data}
        lookup_resp = session.get(url, params=params)
        lookup_resp.raise_for_status()
        results = lookup_resp.json().get("results", [])
        if not results:
            raise

        logger.debug(f"Resource with this name already exists. Retrieved resource: {results[0]}")
        return results[0]


def get(path: str, *, params: Optional[Dict] = None) -> requests.Response:
    session = get_http_session()
    url = f"{settings.url}{path}"
    response = session.get(url, params=params, stream=True)
    response.raise_for_status()

    return response


def create_controller_project(instance: PatternInstance, pattern: Pattern, pattern_def: Dict) -> int:
    """
    Creates a controller project on AAP using the pattern definition.
    Args:
        instance: The PatternInstance object.
        pattern: The related Pattern object.
        pattern_def: The pattern definition dictionary.
    Returns:
        The created project ID.
    """
    project_def = pattern_def["aap_resources"]["controller_project"]
    project_def.update(
        {
            "organization": instance.organization_id,
            "scm_type": "archive",
            "scm_url": pattern.collection_version_uri,
            "credential": instance.credentials.get("project"),
        }
    )

    logger.debug(f"Project definition: {project_def}")
    response = post("/projects/", project_def)

    return response["id"]


def create_execution_environment(instance: PatternInstance, pattern_def: Dict) -> int:
    """
    Creates an execution environment for the controller.
    Args:
        instance: The PatternInstance object.
        pattern_def: The pattern definition dictionary.
    Returns:
        The created execution environment ID.
    """
    ee_def = pattern_def["aap_resources"]["controller_execution_environment"]
    image_name = ee_def.pop("image_name")
    ee_def.update(
        {
            "organization": instance.organization_id,
            "credential": instance.credentials.get("ee"),
            "image": f"{urlparse.urlparse(AAP_SETTINGS.url).netloc}/{image_name}",
            "pull": ee_def.get("pull") or "missing",
        }
    )
    logger.debug(f"Execution Environment definition: {ee_def}")
    response = post("/execution_environments/", ee_def)

    return response["id"]


def create_labels(instance: PatternInstance, pattern_def: Dict) -> List[ControllerLabel]:
    """
    Creates controller labels and returns model instances.
    Args:
        instance: The PatternInstance object.
        pattern_def: The pattern definition dictionary.
    Returns:
        List of ControllerLabel model instances.
    """
    labels = []
    for name in pattern_def["aap_resources"]["controller_labels"]:
        label_def = {"name": name, "organization": instance.organization_id}
        logger.debug(f"Creating label with definition: {label_def}")

        results = post("/labels/", label_def)
        label_obj, _ = ControllerLabel.objects.get_or_create(label_id=results["id"])
        labels.append(label_obj)

    return labels


def create_job_templates(instance: PatternInstance, pattern_def: Dict, project_id: int, ee_id: int) -> List[Dict[str, Any]]:
    """
    Creates job templates and associated surveys.
    Args:
        instance: The PatternInstance object.
        pattern_def: The pattern definition dictionary.
        project_id: Controller project ID.
        ee_id: Execution environment ID.
    Returns:
        List of dictionaries describing created automations.
    """
    automations = []
    jt_defs = pattern_def["aap_resources"]["controller_job_templates"]

    for jt in jt_defs:
        survey = jt.pop("survey", None)
        primary = jt.pop("primary", False)

        jt_payload = {
            **jt,
            "organization": instance.organization_id,
            "project": project_id,
            "execution_environment": ee_id,
            "playbook": f"extensions/patterns/{pattern_def['name']}/playbooks/{jt['playbook']}",
            "ask_inventory_on_launch": True,
        }

        logger.debug(f"Creating job template with payload: {jt_payload}")
        jt_res = post("/job_templates/", jt_payload)
        jt_id = jt_res["id"]

        if survey:
            logger.debug(f"Adding survey to job template {jt_id}")
            post(f"/job_templates/{jt_id}/survey_spec/", {"spec": survey})

        automations.append({"type": "job_template", "id": jt_id, "primary": primary})

    return automations


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
        instance.controller_project_id = project_id
        instance.controller_ee_id = ee_id
        instance.save()
        for label in labels:
            instance.controller_labels.add(label)
        for auto in automations:
            instance.automations.create(
                automation_type=auto["type"],
                automation_id=auto["id"],
                primary=auto["primary"],
            )


def assign_execute_roles(executors: Dict[str, List[Any]], automations: List[Dict[str, Any]]) -> None:
    """
    Assigns JobTemplate Execute role to teams and users.
    Args:
        executors: Dictionary with "teams" and "users" lists.
        automations: List of job template metadata.
    """
    if not executors["teams"] and not executors["users"]:
        return

    # Get role ID for "Execute" on JobTemplate
    roles_resp = get("/roles/", params={"name": "Execute", "content_type": "job_template"})
    if not roles_resp["results"]:
        raise ValueError("Could not find 'JobTemplate Execute' role.")

    role_id = roles_resp["results"][0]["id"]

    for auto in automations:
        jt_id = auto["id"]
        for team_id in executors.get("teams", []):
            post(
                "/role_assignments/",
                {
                    "discriminator": "team",
                    "assignee_id": str(team_id),
                    "content_type": "job_template",
                    "object_id": jt_id,
                    "role_id": role_id,
                },
            )
        for user_id in executors.get("users", []):
            post(
                "/role_assignments/",
                {
                    "discriminator": "user",
                    "assignee_id": str(user_id),
                    "content_type": "job_template",
                    "object_id": jt_id,
                    "role_id": role_id,
                },
            )


def run_pattern_task(pattern_id: int, task_id: int):
    """
    Orchestrates downloading a collection and saving a pattern definition.
    """
    task = Task.objects.get(id=task_id)

    try:
        pattern = Pattern.objects.get(id=pattern_id)
        update_task_status(task, "Running", {"info": "Processing pattern"})

        # Get all necessary names from the pattern object
        collection_name = pattern.collection_name.replace(".", "-")
        collection_version = pattern.collection_version
        pattern_name = pattern.pattern_name

        update_task_status(task, "Running", {"info": "Downloading collection tarball"})

        with download_collection(collection_name, collection_version) as collection_path:
            path_to_definition = os.path.join(collection_path, "extensions", "patterns", pattern_name, "meta", "pattern.json")

            with open(path_to_definition, "r") as file:
                definition = json.load(file)

            pattern.pattern_definition = definition
            pattern.collection_version_uri = pattern.collection_version_uri
            pattern.save(update_fields=["pattern_definition", "collection_version_uri"])

        update_task_status(task, "Completed", {"info": "Pattern processed successfully"})

    except FileNotFoundError:
        logger.error(f"Could not find pattern definition for task {task_id}")
        update_task_status(task, "Failed", {"error": "Pattern definition file not found in collection."})

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        update_task_status(task, "Failed", {"error": str(e)})


def run_pattern_instance_task(instance_id: int, task_id: int):
    task = Task.objects.get(id=task_id)

    try:
        instance = PatternInstance.objects.select_related("pattern").get(id=instance_id)
        pattern = instance.pattern
        pattern_def = pattern.pattern_definition or {}

        update_task_status(task, "Running", {"info": "Processing PatternInstance"})

        if not pattern_def:
            raise ValueError("Pattern definition is missing.")

        update_task_status(task, "Running", {"info": "Creating controller project"})
        project_id = create_controller_project(instance, pattern, pattern_def)

        update_task_status(task, "Running", {"info": "Creating execution environment"})
        ee_id = create_execution_environment(instance, pattern_def)

        update_task_status(task, "Running", {"info": "Creating controller labels"})
        labels = create_labels(instance, pattern_def)

        update_task_status(task, "Running", {"info": "Creating job templates"})
        automations = create_job_templates(instance, pattern_def, project_id, ee_id)

        update_task_status(task, "Running", {"info": "Saving instance and related objects"})
        save_instance_state(instance, project_id, ee_id, labels, automations)

        update_task_status(task, "Running", {"info": "Assigning executor roles"})
        assign_execute_roles(instance.executors, automations)

        update_task_status(task, "Completed", {"info": "PatternInstance processed"})
    except Exception as e:
        logger.exception("Failed to process PatternInstance.")
        update_task_status(task, "Failed", {"error": str(e)})
