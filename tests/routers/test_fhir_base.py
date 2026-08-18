from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.conftest import make_list_resource
from tests.routers.conftest import TEST_URA, make_auth_context, make_test_client

FHIR_JSON = {"Content-Type": "application/fhir+json"}


@pytest.fixture()
def client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
) -> TestClient:
    key_info_service.add_one("nvi-label", "AES_CBC")
    return make_test_client(referral_service, crypto_client, key_info_service, make_auth_context())


def _bundle(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"resourceType": "Bundle", "type": "transaction", "entry": list(entries)}


def _post_entry(ura: str = TEST_URA) -> dict[str, Any]:
    return {
        "request": {"method": "POST", "url": "List"},
        "resource": make_list_resource(ura=ura).model_dump(by_alias=True, exclude_none=True, mode="json"),
    }


class TestRegisterBundle:
    def test_processes_a_post_entry(self, client: TestClient) -> None:
        response = client.post("/fhir", json=_bundle(_post_entry()), headers=FHIR_JSON)

        assert response.status_code == 200
        entry = response.json()["entry"][0]
        assert entry["response"]["status"] == "200"
        assert entry["resource"]["id"] is not None

    def test_rejects_an_empty_bundle(self, client: TestClient) -> None:
        response = client.post("/fhir", json=_bundle(), headers=FHIR_JSON)

        assert response.status_code == 400

    def test_reports_per_entry_outcomes_independently(self, client: TestClient) -> None:
        # One valid entry alongside one for another URA: the bundle still succeeds and
        # the failing entry carries its own status.
        response = client.post(
            "/fhir",
            json=_bundle(_post_entry(), _post_entry(ura="99999999")),
            headers=FHIR_JSON,
        )

        assert response.status_code == 200
        statuses = [e["response"]["status"] for e in response.json()["entry"]]
        assert statuses == ["200", "403"]

    def test_processes_a_get_query_entry(self, client: TestClient) -> None:
        client.post("/fhir", json=_bundle(_post_entry()), headers=FHIR_JSON)

        response = client.post(
            "/fhir",
            json=_bundle({"request": {"method": "GET", "url": "List?source:identifier=SRC-001"}}),
            headers=FHIR_JSON,
        )

        assert response.status_code == 200
        entry = response.json()["entry"][0]
        assert entry["response"]["status"] == "200"
        assert entry["resource"]["resourceType"] == "Bundle"
