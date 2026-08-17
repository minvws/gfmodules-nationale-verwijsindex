from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.auth.data import AuthorizationScope
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.conftest import TEST_PSEUDONYM_TOKEN, make_list_resource
from tests.routers.conftest import (
    TEST_SOURCE_ID,
    make_auth_context,
    make_localize_auth_context,
    make_test_client,
)

FHIR_JSON = {"Content-Type": "application/fhir+json"}


def _body(**kwargs: Any) -> dict[str, Any]:
    return make_list_resource(**kwargs).model_dump(by_alias=True, exclude_none=True, mode="json")


@pytest.fixture()
def client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
) -> TestClient:
    """Managing client authenticated as TEST_SOURCE_ID with create/read/delete scopes."""
    key_info_service.add_one("nvi-label", "AES_CBC")
    return make_test_client(referral_service, crypto_client, key_info_service, make_auth_context())


@pytest.fixture()
def localize_client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
) -> TestClient:
    """Client with LOCALIZE scope only and no source_id in its claims."""
    key_info_service.add_one("nvi-label", "AES_CBC")
    return make_test_client(referral_service, crypto_client, key_info_service, make_localize_auth_context())


class TestCreate:
    def test_creates_list_resource(self, client: TestClient) -> None:
        response = client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        assert response.status_code == 201
        assert response.json()["resourceType"] == "List"

    def test_is_idempotent(self, client: TestClient) -> None:
        first = client.post("/fhir/List", json=_body(), headers=FHIR_JSON)
        second = client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        assert first.status_code == 201
        assert second.status_code == 201
        # The duplicate returns the stored record rather than creating a second one.
        assert second.json()["id"] == first.json()["id"]

    def test_rejects_source_that_differs_from_claims(self, client: TestClient) -> None:
        response = client.post("/fhir/List", json=_body(source_id="SOMEONE-ELSE"), headers=FHIR_JSON)

        assert response.status_code == 403

    def test_requires_create_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        client = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(scopes=[AuthorizationScope.READ]),
        )

        response = client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        assert response.status_code == 403

    def test_rejects_a_caller_without_a_source_id(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        client = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(source_id=None),
        )

        response = client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        assert response.status_code == 403


class TestGet:
    def test_returns_created_resource(self, client: TestClient) -> None:
        created = client.post("/fhir/List", json=_body(), headers=FHIR_JSON).json()

        response = client.get(f"/fhir/List/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_requires_read_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        client = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(scopes=[AuthorizationScope.CREATE]),
        )

        response = client.get("/fhir/List/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 403


class TestQuery:
    def test_returns_bundle_for_own_source(self, client: TestClient) -> None:
        client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        response = client.get("/fhir/List", params={"source:identifier": TEST_SOURCE_ID})

        assert response.status_code == 200
        assert response.json()["resourceType"] == "Bundle"

    def test_rejects_source_that_differs_from_claims(self, client: TestClient) -> None:
        response = client.get("/fhir/List", params={"source:identifier": "SOMEONE-ELSE"})

        assert response.status_code == 403

    def test_localize_query_needs_no_source_match(self, localize_client: TestClient) -> None:
        response = localize_client.get("/fhir/List", params={"subject:identifier": TEST_PSEUDONYM_TOKEN})

        assert response.status_code == 200
        assert response.json()["resourceType"] == "Bundle"

    def test_localize_query_requires_localize_scope(self, client: TestClient) -> None:
        response = client.get("/fhir/List", params={"subject:identifier": TEST_PSEUDONYM_TOKEN})

        assert response.status_code == 403

    def test_source_query_requires_only_read_scope(self, client: TestClient) -> None:
        response = client.get(
            "/fhir/List",
            params={"subject:identifier": TEST_PSEUDONYM_TOKEN, "source:identifier": TEST_SOURCE_ID},
        )

        assert response.status_code == 200


class TestDelete:
    def test_deletes_by_id(self, client: TestClient) -> None:
        created = client.post("/fhir/List", json=_body(), headers=FHIR_JSON).json()

        response = client.delete(f"/fhir/List/{created['id']}")

        assert response.status_code == 200

    def test_delete_by_id_requires_a_source_id(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        client = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(source_id=None),
        )

        response = client.delete("/fhir/List/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 403

    def test_delete_by_id_hides_another_sources_resource_behind_404(
        self,
        client: TestClient,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        created = client.post("/fhir/List", json=_body(), headers=FHIR_JSON).json()
        sibling = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(source_id="SRC-002"),
        )

        response = sibling.delete(f"/fhir/List/{created['id']}")

        assert response.status_code == 404
        assert client.get(f"/fhir/List/{created['id']}").status_code == 200

    def test_delete_by_query_requires_a_source_id(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        client = make_test_client(
            referral_service,
            crypto_client,
            key_info_service,
            make_auth_context(source_id=None),
        )

        response = client.delete("/fhir/List", params={"subject:identifier": TEST_PSEUDONYM_TOKEN})

        assert response.status_code == 403

    def test_delete_by_query_rejects_source_that_differs_from_claims(self, client: TestClient) -> None:
        response = client.delete("/fhir/List", params={"source:identifier": "SOMEONE-ELSE"})

        assert response.status_code == 403

    def test_delete_by_query_accepts_own_source(self, client: TestClient) -> None:
        client.post("/fhir/List", json=_body(), headers=FHIR_JSON)

        response = client.delete("/fhir/List", params={"source:identifier": TEST_SOURCE_ID})

        assert response.status_code == 200

    def test_delete_by_query_reports_not_found_when_nothing_matched(self, client: TestClient) -> None:
        # Nothing was registered, so the bulk delete matches no rows.
        response = client.delete("/fhir/List", params={"source:identifier": TEST_SOURCE_ID})

        assert response.status_code == 404
        assert response.json()["issue"][0]["code"] == "not-found"
