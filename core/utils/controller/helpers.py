import contextlib
import logging
import os
import random
import shutil
import tarfile
import tempfile
import time
import urllib.parse
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from requests.exceptions import HTTPError
from requests.exceptions import RequestException
from requests.exceptions import Timeout

from core.models import ControllerLabel
from core.models import Pattern
from core.models import PatternInstance

from ..http_helpers import RetryError
from .client import get
from .client import get_http_session
from .client import post

logger = logging.getLogger(__name__)


def build_collection_uri(collection: str, version: str) -> str:
    """
    Builds the full URI for a given collection and version.
    Args:
        collection (str): The collection name.
        version (str): The version string.
    Returns:
        str: The full URI to the collection artifact.
    """
    path = "/api/galaxy/v3/plugin/ansible/content/published/collections/artifacts"
    filename = f"{collection}-{version}.tar.gz"

    return urljoin(f"{settings.AAP_URL}/", f"{path}/{filename}")


@contextlib.contextmanager
def download_collection(collection_name: str, version: str) -> Iterator[str]:
    """
    Downloads and extracts a collection tarball from private automation hub to a
    temporary directory.
    Args:
        collection (str): The name of the collection (e.g., 'my_namespace.my_collection').
        version (str): The version of the collection (e.g., '1.0.0').
    Yields:
        The path to the extracted collection files.
    """
    response = None
    collection = collection_name.replace(".", "-")
    temp_base_dir = tempfile.mkdtemp()
    collection_path = os.path.join(temp_base_dir, f"{collection}-{version}")
    os.makedirs(collection_path, exist_ok=True)
    path = build_collection_uri(collection, version)

    try:
        response = get(path)

        with tarfile.open(fileobj=response.raw, mode="r|gz") as tar:
            tar.extractall(path=collection_path, filter="data")

        logger.info(f"Collection extracted to {collection_path}")
        yield collection_path  # Yield the path to the caller
    finally:
        shutil.rmtree(temp_base_dir)


def create_project(
    instance: PatternInstance, pattern: Pattern, pattern_def: Dict[str, Any]
) -> int:
    """
    Creates a controller project on AAP using the pattern definition.
    Args:
        instance (PatternInstance): The PatternInstance object.
        pattern (Pattern): The related Pattern object.
        pattern_def (Dict[str, Any]): The pattern definition dictionary.
    Returns:
        The created project ID.
    """
    project_def = pattern_def["aap_resources"]["controller_project"]
    project_def.update(
        {
            "organization": instance.organization_id,
            "scm_type": "archive",
            "scm_url": pattern.collection_version_uri,
            "credential": instance.credentials.get("id"),
        }
    )
    logger.debug(f"Project definition: {project_def}")
    project_id = post("/api/controller/v2/projects/", project_def)["id"]
    wait_for_project_sync(project_id)
    return project_id


def create_execution_environment(
    instance: PatternInstance, pattern_def: Dict[str, Any]
) -> int:
    """
    Creates an execution environment for the controller.
    Args:
        instance (PatternInstance): The PatternInstance object.
        pattern_def (Dict[str, Any]): The pattern definition dictionary.
    Returns:
        The created execution environment ID.
    """
    ee_def = pattern_def["aap_resources"]["controller_execution_environment"]
    image_name = ee_def.pop("image_name")
    ee_def.update(
        {
            "organization": instance.organization_id,
            "credential": instance.credentials.get("ee"),
            "image": f"{settings.AAP_URL.split('//')[-1]}/{image_name}",
            "pull": ee_def.get("pull") or "missing",
        }
    )
    logger.debug(f"Execution Environment definition: {ee_def}")
    return post("/api/controller/v2/execution_environments/", ee_def)["id"]


def create_labels(
    instance: PatternInstance, pattern_def: Dict[str, Any]
) -> List[ControllerLabel]:
    """
    Creates controller labels and returns model instances.
    Args:
        instance (PatternInstance): The PatternInstance object.
        pattern_def (Dict[str, Any]): The pattern definition dictionary.
    Returns:
        List of ControllerLabel model instances.
    """
    labels = []
    for name in pattern_def["aap_resources"]["controller_labels"]:
        label_def = {"name": name, "organization": instance.organization_id}
        logger.debug(f"Creating label with definition: {label_def}")

        results = post("/api/controller/v2/labels/", label_def)
        label_obj, _ = ControllerLabel.objects.get_or_create(label_id=results["id"])
        labels.append(label_obj)

    return labels


def create_job_templates(
    instance: PatternInstance,
    pattern_def: Dict[str, Any],
    project_id: int,
    ee_id: int,
) -> List[Dict[str, Any]]:
    """
    Creates job templates and associated surveys.
    Args:
        instance (PatternInstance): The PatternInstance object.
        pattern_def (Dict[str, Any]): The pattern definition dictionary.
        project_id (int): Controller project ID.
        ee_id (int): Execution environment ID.
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
            "playbook": (
                f"extensions/patterns/{pattern_def['name']}/playbooks/{jt['playbook']}"
            ),
            "ask_inventory_on_launch": True,
        }

        logger.debug(f"Creating job template with payload: {jt_payload}")
        jt_res = post("/api/controller/v2/job_templates/", jt_payload)
        jt_id = jt_res["id"]

        if survey:
            logger.debug(f"Adding survey to job template {jt_id}")
            post(f"/api/controller/v2/job_templates/{jt_id}/survey_spec/", survey)

        automations.append({"type": "job_template", "id": jt_id, "primary": primary})

    return automations


def assign_execute_roles(
    executors: Dict[str, List[Any]], automations: List[Dict[str, Any]]
) -> None:
    """
    Assigns JobTemplate Execute role to teams and users.
    Args:
        executors (Dict[str, List[Any]]): Dictionary with "teams" and "users" lists.
        automations (List[Dict[str, Any]]): List of job template metadata.
    """
    if not executors or (not executors["teams"] and not executors["users"]):
        return

    # Get role ID for "Execute" on JobTemplate
    result = get(
        "/api/controller/v2/roles/",
        params={"name": "Execute", "content_type": "job_template"},
    )
    roles_resp = result.json()
    if not roles_resp["results"]:
        raise ValueError("Could not find 'JobTemplate Execute' role.")

    role_id = roles_resp["results"][0]["id"]

    for auto in automations:
        jt_id = auto["id"]
        for team_id in executors.get("teams", []):
            post(
                "/api/controller/v2/role_assignments/",
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
                "/api/controller/v2/role_assignments/",
                {
                    "discriminator": "user",
                    "assignee_id": str(user_id),
                    "content_type": "job_template",
                    "object_id": jt_id,
                    "role_id": role_id,
                },
            )


def wait_for_project_sync(
    project_id: str,
    *,
    max_retries: int = 15,
    initial_delay: float = 1,
    max_delay: float = 60,
    timeout: float = 30,
) -> None:
    """
    Polls the AAP Controller project endpoint until the project sync completes
    successfully.

    This function checks the sync status of a project using its ID. It will keep
    polling until the status becomes 'successful', or until a maximum number of
    retries is reached. Uses exponential backoff with jitter between retries.

    Args:
        project_id (str): The numeric ID of the project to monitor.
        max_retries (int): Maximum number of times to retry checking the status.
        initial_delay (float): Delay in seconds before the first retry.
        max_delay (float): Upper limit on delay between retries.
        timeout (float): Timeout in seconds for each HTTP request.

    Raises:
        RetryError: If the project does not sync after all retries.
        HTTPError: For non-retryable 4xx/5xx errors.
        RequestException: For connection-related errors (e.g., network failures).
    """
    session = get_http_session()
    url = urllib.parse.urljoin(
        settings.AAP_URL, f"/api/controller/v2/projects/{project_id}"
    )
    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            status = response.json().get("status")
            if status == "successful":
                logger.info(
                    f"Project {project_id} synced successfully on attempt {attempt}."
                )
                return

            logger.info(f"Project {project_id} status: '{status}'. Retrying...")

        except HTTPError as e:
            if (
                e.response.status_code not in (408, 429)
                and 400 <= e.response.status_code < 500
            ):
                raise
            logger.warning(
                f"Retryable HTTP error ({e.response.status_code}) on attempt {attempt}"
            )
        except (Timeout, RequestException) as e:
            logger.warning(f"Network error on attempt {attempt}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt}: {e}")

        if attempt == max_retries:
            raise RetryError(
                f"Project {project_id} failed to sync after {max_retries} attempts."
            )

        jitter = random.uniform(0.8, 1.2)
        sleep_time = min(delay * jitter, max_delay)
        logger.debug(f"Waiting {sleep_time:.2f}s before retry #{attempt + 1}...")
        time.sleep(sleep_time)
        delay *= 2


def save_instance_state(
    instance: PatternInstance,
    project_id: int,
    ee_id: int,
    labels: List[ControllerLabel],
    automations: List[Dict[str, Any]],
) -> None:
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
