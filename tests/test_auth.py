from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.config import set_config
from tests.test_config import get_test_config

VALID_HEADERS = {
    "x-gf-act-sub": "00000000000000000001",
    "x-gf-act-cn": "client.example.nl",
    "x-gf-sub": "00000001",
    "x-gf-audience": "test-audience",
    "x-gf-scope": "nvi:create",
    "x-gf-cert-type": "x",
    "x-gf-organization-name": "Test Organization",
}


@pytest.fixture
def client() -> TestClient:
    set_config(get_test_config())
    return TestClient(setup_fastapi(), raise_server_exceptions=False)


@pytest.mark.parametrize(
    "headers",
    [{}, {**VALID_HEADERS, "x-gf-sub": "not-a-ura"}, {**VALID_HEADERS, "x-gf-scope": "unknown"}],
    ids=["missing", "invalid-ura", "unknown-scope"],
)
def test_rejects_invalid_auth_headers_as_unauthenticated(client: TestClient, headers: dict[str, Any]) -> None:
    response = client.post("/registrations", json={"pseudonym": "p", "oprf_key": "k"}, headers=headers)

    assert response.status_code == 401


def test_reports_invalid_auth_headers_on_a_single_line(client: TestClient) -> None:
    response = client.post(
        "/registrations", json={"pseudonym": "p", "oprf_key": "k"}, headers={**VALID_HEADERS, "x-gf-scope": "unknown"}
    )

    assert response.json() == (
        "Invalid Authorization Headers in request: scope: Value error, x-gf-scope must hold at least one known scope"
    )


def test_asks_a_fhir_client_with_invalid_auth_headers_to_log_in(client: TestClient) -> None:
    response = client.get("/fhir/List", params={"source:identifier": "SRC-001"})

    assert response.status_code == 401
    assert response.json()["issue"][0]["code"] == "login"
