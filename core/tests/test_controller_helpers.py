import os
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests

from core.utils.controller import assign_execute_roles
from core.utils.controller import build_collection_uri
from core.utils.controller import create_execution_environment
from core.utils.controller import create_job_templates
from core.utils.controller import create_labels
from core.utils.controller import create_project
from core.utils.controller import download_collection
from core.utils.controller import save_instance_state
from core.utils.controller.helpers import create_controller_role_assignment
from core.utils.controller.helpers import get_role_definition_id
from core.utils.controller.helpers import wait_for_project_sync


@pytest.fixture
def mock_tar_data():
    """A fixture to provide mock tarball data."""
    return b"This is some mock tarball content"


@pytest.fixture
def mock_session():
    """A fixture to provide a mock requests.Session object."""
    return MagicMock(spec=requests.Session)


@pytest.fixture
def mock_download_success(mock_tar_data):
    """
    Corrected fixture to mock a successful download scenario,
    including mocking os.makedirs and ensuring cleanup.
    """
    with (
        patch("core.utils.controller.helpers.get") as mock_get,
        patch("core.utils.controller.helpers.tarfile.open") as mock_tar_open,
        patch("core.utils.controller.helpers.os.makedirs") as mock_makedirs,
        patch("core.utils.controller.helpers.shutil.rmtree") as mock_rmtree,
        patch(
            "core.utils.controller.helpers.tempfile.mkdtemp",
            return_value="/mock/temp/dir",
        ) as mock_mkdtemp,
    ):

        mock_response = MagicMock()
        mock_response.raw = mock_tar_data
        mock_get.return_value = mock_response

        mock_tar_open.return_value.__enter__.return_value = MagicMock()

        yield mock_get, mock_tar_open, mock_makedirs, mock_mkdtemp, mock_rmtree


@pytest.fixture
def mock_download_failure():
    """
    Fixture to mock a download failure scenario by raising an exception
    and mocking the cleanup functions.
    """
    with (
        patch(
            "core.utils.controller.helpers.get", side_effect=Exception("Network error")
        ) as mock_get,
        patch("core.utils.controller.helpers.shutil.rmtree") as mock_rmtree,
        patch("core.utils.controller.helpers.os.makedirs"),
        patch(
            "core.utils.controller.helpers.tempfile.mkdtemp",
            return_value="/mock/temp/dir",
        ) as mock_mkdtemp,
    ):

        yield mock_get, mock_rmtree, mock_mkdtemp


@pytest.mark.parametrize(
    "collection_name, version, expected_uri",
    [
        (
            "another.collection",
            "2.0.0",
            (
                "http://localhost:44926/api/galaxy/v3/plugin/ansible/content/published/"
                "collections/artifacts/another-collection-2.0.0.tar.gz"
            ),
        ),
        (
            "edge.case",
            "0.1.0-beta",
            (
                "http://localhost:44926/api/galaxy/v3/plugin/ansible/content/published/"
                "collections/artifacts/edge-case-0.1.0-beta.tar.gz"
            ),
        ),
    ],
)
def test_build_collection_uri(collection_name, version, expected_uri):
    """
    Tests that various collection names and versions build the correct URI.
    """
    assert build_collection_uri(collection_name, version) == expected_uri


def test_download_collection_success(mock_download_success):
    """
    Tests the successful download and extraction of a collection.
    """
    mock_get, mock_tar_open, mock_makedirs, mock_mkdtemp, mock_rmtree = (
        mock_download_success
    )

    collection_name = "my_namespace.my_collection"
    version = "1.0.0"
    expected_path = os.path.join("/mock/temp/dir", "my_namespace.my_collection-1.0.0")

    with download_collection(collection_name, version) as path:
        # Assert that the correct path was yielded
        assert path == expected_path

        mock_mkdtemp.assert_called_once()
        mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)
        mock_get.assert_called_once()
        mock_tar_open.assert_called_once()

    mock_rmtree.assert_called_once_with("/mock/temp/dir")


def test_download_collection_failure(mock_download_failure):
    """
    Tests that an exception during download.
    """
    mock_get, mock_rmtree, mock_mkdtemp = mock_download_failure

    collection_name = "my_namespace.my_collection"
    version = "1.0.0"

    with pytest.raises(Exception, match="Network error"):
        with download_collection(collection_name, version):
            pass

    mock_mkdtemp.assert_called_once()
    mock_rmtree.assert_called_once_with("/mock/temp/dir")


@patch("core.utils.controller.helpers.post")
@patch("core.utils.controller.helpers.wait_for_project_sync")
def test_create_project_builds_payload_and_waits(mock_wait, mock_post, mock_session):
    instance = MagicMock(organization_id=7, credentials={"project": 123})
    pattern = MagicMock(
        collection_version_uri="https://hub/artifacts/collection-1.0.0.tar.gz",
        pattern_definition={
            "aap_resources": {
                "controller_project": {"name": "proj", "scm_type": "git"},
            }
        },
    )

    mock_post.return_value = {"id": 55}

    pid = create_project(mock_session, instance, pattern)

    assert pid == 55
    payload = mock_post.call_args.args[2]
    print("payload", payload)
    assert payload["organization"] == 7
    assert payload["scm_type"] == "archive"
    assert payload["scm_url"] == "https://hub/artifacts/collection-1.0.0.tar.gz"
    assert payload["credential"] == 123
    mock_wait.assert_called_once_with(mock_session, 55)


@patch("core.utils.controller.helpers.post")
@patch("core.utils.controller.helpers.settings.AAP_URL", "https://aap.example.com")
@pytest.mark.parametrize(
    "ee_def,expected_pull",
    [
        ({"name": "ee1", "image_name": "ns/repo:tag"}, ""),
        ({"name": "ee1", "image_name": "ns/repo:tag", "pull": "always"}, "always"),
    ],
)
def test_create_execution_environment_pull(
    mock_post, ee_def, expected_pull, mock_session
):
    instance = MagicMock(organization_id=3, credentials={"ee": 777})
    pattern_def = {"aap_resources": {"controller_execution_environment": dict(ee_def)}}
    mock_post.return_value = {"id": 99}
    _ = create_execution_environment(mock_session, instance, pattern_def)
    payload = mock_post.call_args.args[2]
    assert payload["image"] == "aap.example.com/ns/repo:tag"
    assert payload["pull"] == expected_pull


@patch("core.utils.controller.helpers.ControllerLabel")
@patch("core.utils.controller.helpers.post")
def test_create_labels(mock_post, MockControllerLabel, mock_session):
    instance = MagicMock(organization_id=1)
    pattern_def = {"aap_resources": {"controller_labels": ["L1", "L2"]}}

    mock_post.side_effect = [
        {"id": 10},
        {"id": 20},
    ]
    label1 = MagicMock()
    label2 = MagicMock()
    MockControllerLabel.objects.get_or_create.side_effect = [
        (label1, True),
        (label2, False),
    ]

    labels = create_labels(mock_session, instance, pattern_def)

    assert labels == [label1, label2]
    # Ensure proper payloads used
    first_payload = mock_post.call_args_list[0].args[2]
    assert first_payload == {"name": "L1", "organization": 1}


@patch("core.utils.controller.helpers.post")
def test_create_job_templates_payload_and_survey(mock_post, mock_session):
    instance = MagicMock(organization_id=5)
    pattern_def = {
        "name": "mypat",
        "aap_resources": {
            "controller_job_templates": [
                {
                    "name": "jt1",
                    "playbook": "run.yml",
                    "survey": {"spec": 1},
                    "primary": True,
                },
                {"name": "jt2", "playbook": "test.yml"},
            ]
        },
    }

    # Calls happen in order: create jt1, survey jt1, create jt2
    mock_post.side_effect = [
        {"id": 11},  # create jt1
        None,  # survey jt1 (return value ignored)
        {"id": 22},  # create jt2
    ]

    autos = create_job_templates(
        mock_session, instance, pattern_def, project_id=10, ee_id=20
    )

    assert autos == [
        {"type": "job_template", "id": 11, "primary": True},
        {"type": "job_template", "id": 22, "primary": False},
    ]

    # Survey endpoint called once for jt1
    survey_calls = [
        args for args, _ in mock_post.call_args_list if "/survey_spec/" in args[1]
    ]
    assert len(survey_calls) == 1

    # Verify payload fields for a JT
    first_jt_payload = mock_post.call_args_list[0].args[2]
    assert first_jt_payload["organization"] == 5
    assert first_jt_payload["project"] == 10
    assert first_jt_payload["execution_environment"] == 20
    assert first_jt_payload["ask_inventory_on_launch"] is True
    assert first_jt_payload["playbook"] == "extensions/patterns/mypat/playbooks/run.yml"


@patch("core.utils.controller.helpers.get_role_definition_id")
@patch("core.utils.controller.helpers.post")
def test_assign_execute_roles(mock_post, mock_get_role_definition_id, mock_session):
    mock_get_role_definition_id.return_value = 7
    automations = [{"id": 1}, {"id": 2}]
    executors = {"teams": [100, 200], "users": [300]}

    assign_execute_roles(mock_session, executors, automations)

    # 1 role lookup, then 2 JTs * (2 teams + 1 user) = 6 role assignments
    assert mock_post.call_count == 6


@patch("core.utils.controller.helpers.get_role_definition_id")
@patch("core.utils.controller.helpers.post")
def test_assign_execute_roles_role_not_found_raises(
    mock_post, mock_get_role_definition_id, mock_session
):
    # Set the return value of the mocked get_role_definition_id to None
    mock_get_role_definition_id.return_value = None

    with pytest.raises(ValueError, match="Could not find 'JobTemplate Execute' role."):
        assign_execute_roles(mock_session, {"teams": [1], "users": []}, [{"id": 1}])

    # Ensure that no post calls were made
    mock_post.assert_not_called()


@patch("core.utils.controller.helpers.get_role_definition_id")
@patch("core.utils.controller.helpers.post")
def test_assign_execute_roles_no_executors_early_return(
    mock_post, mock_get_session, mock_session
):
    assign_execute_roles(mock_session, {"teams": [], "users": []}, [{"id": 1}])
    mock_get_session.assert_not_called()
    mock_post.assert_not_called()


def test_wait_for_project_sync_eventual_success(mock_session):
    with (
        patch("core.utils.controller.helpers.time.sleep", return_value=None),
        patch("core.utils.controller.helpers.random.uniform", return_value=1.0),
        patch(
            "core.utils.controller.helpers.settings.AAP_URL", "https://aap.example.com"
        ),
    ):
        # two polls: pending -> successful
        resp_pending = MagicMock(
            json=lambda: {"status": "pending"}, raise_for_status=lambda: None
        )
        resp_success = MagicMock(
            json=lambda: {"status": "successful"}, raise_for_status=lambda: None
        )

        mock_session.get.side_effect = [resp_pending, resp_success]

        wait_for_project_sync(
            mock_session,
            "42",
            max_retries=5,
            initial_delay=0.001,
            max_delay=0.002,
            timeout=0.001,
        )

        assert mock_session.get.call_count == 2


def test_wait_for_project_sync_success_first_try(mock_session):
    with (
        patch(
            "core.utils.controller.helpers.settings.AAP_URL", "https://aap.example.com"
        ),
    ):
        resp_success = MagicMock()
        resp_success.raise_for_status.return_value = None
        resp_success.json.return_value = {"status": "successful"}

        mock_session.get.return_value = resp_success

        wait_for_project_sync(mock_session, "10")
        mock_session.get.assert_called_once()


def test_wait_for_project_sync_non_retryable_4xx_raises(mock_session):
    with (
        patch("core.utils.controller.helpers.time.sleep", return_value=None),
        patch(
            "core.utils.controller.helpers.settings.AAP_URL", "https://aap.example.com"
        ),
    ):
        bad_response = MagicMock()
        bad_response.status_code = 400

        def raise_http():
            err = requests.exceptions.HTTPError("bad")
            err.response = bad_response
            raise err

        bad = MagicMock()
        bad.raise_for_status.side_effect = raise_http
        mock_session.get.return_value = bad

        with pytest.raises(requests.exceptions.HTTPError):
            wait_for_project_sync(
                mock_session,
                "99",
                max_retries=2,
                initial_delay=0,
                max_delay=0,
                timeout=0.001,
            )


def test_wait_for_project_sync_timeout_then_retry_then_fail(mock_session):
    with (
        patch("core.utils.controller.helpers.time.sleep", return_value=None),
        patch("core.utils.controller.helpers.random.uniform", return_value=1.0),
        patch(
            "core.utils.controller.helpers.settings.AAP_URL", "https://aap.example.com"
        ),
    ):
        # Two timeouts then give up after max_retries
        mock_session.get.side_effect = [
            requests.exceptions.Timeout("t1"),
            requests.exceptions.Timeout("t2"),
            requests.exceptions.Timeout("t3"),
        ]

        from core.utils.controller.helpers import RetryError

        with pytest.raises(RetryError):
            wait_for_project_sync(
                mock_session,
                "77",
                max_retries=3,
                initial_delay=0.001,
                max_delay=0.001,
                timeout=0.001,
            )

        assert mock_session.get.call_count == 3


@patch("core.utils.controller.helpers.transaction.atomic")
def test_save_instance_state_updates_and_links(mock_atomic):
    mock_atomic.return_value.__enter__.return_value = None
    mock_atomic.return_value.__exit__.return_value = None
    instance = MagicMock()
    labels = [MagicMock(), MagicMock()]
    autos = [{"type": "job_template", "id": 1, "primary": True}]

    save_instance_state(
        instance, project_id=10, ee_id=20, labels=labels, automations=autos
    )

    assert instance.controller_project_id == 10
    assert instance.controller_ee_id == 20
    instance.save.assert_called_once()
    instance.controller_labels.add.assert_any_call(labels[0])
    instance.controller_labels.add.assert_any_call(labels[1])
    instance.automations.create.assert_called_once_with(
        automation_type="job_template", automation_id=1, primary=True
    )


def test_get_role_definition_id_found(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"id": "123"}]}
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    role_id = get_role_definition_id(mock_session, "JobTemplate Execute")
    assert role_id == "123"
    mock_session.get.assert_called_once()


def test_get_role_definition_id_not_found(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    role_id = get_role_definition_id(mock_session, "NonExistentRole")
    assert role_id is None
    mock_session.get.assert_called_once()


def test_get_role_definition_id_http_error(mock_session):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=MagicMock(text="error")
    )
    mock_session.get.return_value = mock_response

    role_id = get_role_definition_id(mock_session, "JobTemplate Execute")
    assert role_id is None
    mock_session.get.assert_called_once()


@patch("core.utils.controller.helpers.post")
def test_create_controller_role_assignment_team(mock_post):
    create_controller_role_assignment(
        mock_session,
        assignee_type="team",
        object_id="10",
        role_id="20",
        assignee_id="100",
    )

    expected_data = {
        "object_id": "10",
        "role_definition": "20",
        "team_ansible_id": "100",
    }

    mock_post.assert_called_once_with(
        mock_session, "/api/controller/v2/role_team_assignments/", expected_data
    )


@patch("core.utils.controller.helpers.post")
def test_create_controller_role_assignment_user(mock_post):
    create_controller_role_assignment(
        mock_session,
        assignee_type="user",
        object_id="10",
        role_id="20",
        assignee_id="300",
    )

    expected_data = {
        "object_id": "10",
        "role_definition": "20",
        "user_ansible_id": "300",
    }

    mock_post.assert_called_once_with(
        mock_session, "/api/controller/v2/role_user_assignments/", expected_data
    )
