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


def test_reports_invalid_auth_headers_on_a_single_line(client: TestClient) -> None:
    response = client.post(
        "/registrations", json={"pseudonym": "p", "oprf_key": "k"}, headers={**VALID_HEADERS, "x-gf-scope": "unknown"}
    )

    assert response.json() == (
        "Invalid Authorization Headers in request: scope: Value error, x-gf-scope must hold at least one known scope"
    )
