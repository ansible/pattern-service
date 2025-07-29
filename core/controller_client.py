import json
import logging
import random
import time
import urllib.parse
from functools import wraps
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import TypeVar

import requests
from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from requests.exceptions import RequestException
from requests.exceptions import Timeout

from pattern_service.settings.aap import get_aap_settings

from .models import ControllerLabel
from .models import Pattern
from .models import PatternInstance

logger = logging.getLogger(__name__)

_aap_session: Optional[Session] = None

settings = get_aap_settings()

F = TypeVar("F", bound=Callable[..., requests.Response])


class RetryError(Exception):
    """Custom exception raised when a retry limit is reached."""

    def __init__(
        self, msg: str, request: Optional[Any] = None, response: Optional[Any] = None
    ) -> None:
        super().__init__(msg)
        self.request = request
        self.response = response


def build_collection_uri(collection: str, version: str) -> str:
    """Builds the URI for a given collection and version."""
    base_url = settings.url
    path = "/api/galaxy/v3/plugin/ansible/content/published/collections/artifacts"
    filename = f"{collection}-{version}.tar.gz"

    return f"{base_url}{path}/{filename}"


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
        settings.url, f"/api/controller/v2/projects/{project_id}"
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


def get_http_session(force_refresh: bool = False) -> Session:
    """Returns a cached Session instance with AAP credentials."""
    global _aap_session
    if _aap_session is None or force_refresh:
        session = Session()
        session.auth = HTTPBasicAuth(settings.username, settings.password)
        session.verify = settings.verify_ssl
        session.headers.update({"Content-Type": "application/json"})
        _aap_session = session
    return _aap_session


def safe_json(func: F) -> Callable[..., dict[str, Any]]:
    """
    Decorator for functions that return a `requests.Response`.
    It attempts to parse JSON safely and falls back to raw text if needed.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        response = func(*args, **kwargs)
        try:
            return response.json()
        except ValueError:
            logger.warning(f"Non-JSON response from {response.url}: {response.text!r}")
            return {
                "detail": "Non-JSON response",
                "text": response.text,
                "status_code": response.status_code,
                "url": response.url,
            }

    return wrapper


def post(
    path: str,
    data: Dict,
    *,
    dedupe_keys: Sequence[str] = ("name", "organization"),
) -> Dict[str, Any]:
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

        # Safely parse response JSON
        return safe_json(lambda: response)()

    except requests.exceptions.HTTPError as exc:
        response = exc.response
        if response.status_code != 400:
            raise

        try:
            error_json = safe_json(lambda: response)()
        except Exception:
            error_json = {"detail": response.text}

        logger.warning(f"AAP POST {url} failed with 400. Error response: {error_json}")
        logger.debug(f"Payload sent: {json.dumps(data, indent=2)}")
        logger.debug(f"AAP POST {url} 400; dedup lookup keys: {dedupe_keys}")

        # Attempt deduplication if resource already exists
        params = {k: data[k] for k in dedupe_keys if k in data}
        try:
            lookup_resp = session.get(url, params=params)
            lookup_resp.raise_for_status()
            results = safe_json(lambda: lookup_resp)().get("results", [])

            if results:
                logger.debug(
                    f"Resource already exists. Returning existing resource: {results[0]}"
                )
                return results[0]
        except Exception as e:
            logger.debug(
                f"Deduplication GET failed for {url} with params {params}: {e}"
            )

        # If dedupe fails or no match found, raise with full detail
        raise requests.HTTPError(
            f"400 Bad Request for {url}.\n"
            f"Payload: {json.dumps(data, indent=2)}\n"
            f"Response: {json.dumps(error_json, indent=2)}",
            response=response,
        )


def get(path: str, params: Optional[Dict] = None) -> requests.Response:
    session = get_http_session()
    url = f"{settings.url}{path}"
    response = session.get(url, params=params, stream=True)
    response.raise_for_status()
    return response


def create_project(
    instance: PatternInstance, pattern: Pattern, pattern_def: Dict
) -> int:
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
            "credential": instance.credentials.get("id"),
        }
    )
    logger.debug(f"Project definition: {project_def}")
    project_id = post("/api/controller/v2/projects/", project_def)["id"]
    wait_for_project_sync(project_id)
    return project_id


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
            "image": f"{settings.url.split('//')[-1]}/{image_name}",
            "pull": ee_def.get("pull") or "missing",
        }
    )
    logger.debug(f"Execution Environment definition: {ee_def}")
    return post("/api/controller/v2/execution_environments/", ee_def)["id"]


def create_labels(
    instance: PatternInstance, pattern_def: Dict
) -> List[ControllerLabel]:
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

        results = post("/api/controller/v2/labels/", label_def)
        label_obj, _ = ControllerLabel.objects.get_or_create(label_id=results["id"])
        labels.append(label_obj)

    return labels


def create_job_templates(
    instance: PatternInstance, pattern_def: Dict, project_id: int, ee_id: int
) -> List[Dict[str, Any]]:
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
        executors: Dictionary with "teams" and "users" lists.
        automations: List of job template metadata.
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
