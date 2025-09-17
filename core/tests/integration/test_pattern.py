import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_create_pattern():
    client = APIClient()
    data = {
        "collection_name": "cloud.testing",
        "collection_version": "4.3.2",
        "pattern_name": "new_pattern",
    }
    response = client.post("/api/pattern-service/v1/patterns/", data, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "task_id" in response.data
    assert "message" in response.data
    assert (
        response.data["message"]
        == "Pattern creation initiated. Check task status for progress."
    )
