import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gfmodules.logging.testing import assert_event_emitted, capture_records

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.logging.events import Log
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.conftest import make_list_resource
from tests.routers.conftest import TEST_URA, make_auth_context, make_test_client
from tests.test_config import get_test_config

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
        assert entry["response"]["status"] == "201"
        assert entry["resource"]["id"] is not None

    def test_keeps_the_subject_token_out_of_the_logs_of_a_rejected_entry(self, client: TestClient) -> None:
        entry = {"request": {"method": "DELETE", "url": "List?subject:identifier=urn:wrong|leaky-token-value"}}
        with capture_records("app") as records:
            response = client.post("/fhir", json=_bundle(entry), headers=FHIR_JSON)

        assert response.json()["entry"][0]["response"]["status"] == "422"
        assert not [entry for entry in records if "leaky-token-value" in json.dumps(entry.payload)]

    def test_rejects_a_bundle_over_the_entry_limit_without_processing_it(self, client: TestClient) -> None:
        entries = [_post_entry()] * (get_test_config().bundle.max_entries + 1)
        with capture_records("app") as records:
            response = client.post("/fhir", json=_bundle(*entries), headers=FHIR_JSON)

        assert response.status_code == 413
        assert response.json()["issue"][0]["code"] == "too-costly"
        assert len(records.for_event(Log.INVALID_REQUEST)) == 1
        assert records.for_event(Log.REGISTERED_REFERRAL) == []

    @pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
    def test_rejects_a_body_over_the_size_limit_before_parsing_it(self, client: TestClient, chunked: bool) -> None:
        body = b"x" * (get_test_config().app.max_request_body_bytes + 1)
        content = iter([body]) if chunked else body
        with capture_records("app") as records:
            response = client.post("/fhir", content=content, headers=FHIR_JSON)

        assert response.status_code == 413
        assert response.json()["issue"][0]["code"] == "too-long"
        assert_event_emitted(records, Log.INVALID_REQUEST, http_status=413)

    @pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
    def test_accepts_a_body_of_exactly_the_size_limit(self, client: TestClient, chunked: bool) -> None:
        body = json.dumps(_bundle(_post_entry())).encode().ljust(get_test_config().app.max_request_body_bytes)
        content = iter([body]) if chunked else body
        response = client.post("/fhir", content=content, headers=FHIR_JSON)

        assert response.status_code == 200
        assert response.json()["entry"][0]["response"]["status"] == "201"

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
        assert statuses == ["201", "403"]

    def test_pages_a_get_query_entry(self, client: TestClient) -> None:
        client.post("/fhir", json=_bundle(_post_entry()), headers=FHIR_JSON)

        response = client.post(
            "/fhir",
            json=_bundle({"request": {"method": "GET", "url": "List?source:identifier=SRC-001&_count=1"}}),
            headers=FHIR_JSON,
        )

        result = response.json()["entry"][0]["resource"]
        assert result["total"] == 1
        assert result["link"] == [{"relation": "self", "url": "List?source%3Aidentifier=SRC-001&_count=1&_offset=0"}]

    def test_rejects_paging_parameters_on_a_delete_query_entry(self, client: TestClient) -> None:
        response = client.post(
            "/fhir",
            json=_bundle({"request": {"method": "DELETE", "url": "List?source:identifier=SRC-001&_count=1"}}),
            headers=FHIR_JSON,
        )

        assert response.json()["entry"][0]["response"]["status"] == "422"

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
