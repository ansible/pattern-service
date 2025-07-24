import logging
import requests
from typing import Dict, List, Optional, Sequence
from requests import Session
from requests.auth import HTTPBasicAuth
from pattern_service.settings.aap import get_aap_settings
from .models import Pattern
from .models import PatternInstance
from .models import ControllerLabel
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence


logger = logging.getLogger(__name__)

_aap_session: Optional[Session] = None

settings = get_aap_settings()

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
        params = {k: data[k] for k in dedupe_keys if k in data}
        lookup_resp = session.get(url, params=params)
        lookup_resp.raise_for_status()
        results = lookup_resp.json().get("results", [])
        if not results:
            raise
        logger.debug(f"Resource with this name already exists. Retrieved resource: {results[0]}")
        return results[0]


def get(path: str, params: Optional[Dict] = None) -> requests.Response:
    session = get_http_session()
    url = f"{settings.url}{path}"
    response = session.get(url, params=params, stream=True)
    response.raise_for_status()
    return response


def create_project(instance: PatternInstance, pattern: Pattern, pattern_def: Dict) -> int:
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
    project_def.update({
        "organization": instance.organization_id,
        "scm_type": "archive",
        "scm_url": pattern.collection_version_uri,
        "credential": instance.credentials.get("project"),
    })
    logger.debug(f"Project definition: {project_def}")
    return post("/api/controller/v2/projects/", project_def)["id"]


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
    ee_def.update({
        "organization": instance.organization_id,
        "credential": instance.credentials.get("ee"),
        "image": f"{settings.url.split('//')[-1]}/{image_name}",
        "pull": ee_def.get("pull") or "missing",
    })
    logger.debug(f"Execution Environment definition: {ee_def}")
    return post("/api/controller/v2/execution_environments/", ee_def)["id"]


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

        results = post("/api/controller/v2/labels/", label_def)
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
        jt_res = post("/api/controller/v2/job_templates/", jt_payload)
        jt_id = jt_res["id"]

        if survey:
            logger.debug(f"Adding survey to job template {jt_id}")
            post(f"/api/controller/v2/job_templates/{jt_id}/survey_spec/", {"spec": survey})

        automations.append({"type": "job_template", "id": jt_id, "primary": primary})

    return automations


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
    result = get("/api/controller/v2/roles/", params={"name": "Execute", "content_type": "job_template"})
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
