import pytest
from fastapi.testclient import TestClient

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.auth.data import AuthorizationRole, AuthorizationScope
from app.services.referral_service import ReferralService
from tests.routers.v1.conftest import (
    TEST_SOURCE_ID,
    TEST_URA,
    make_auth_context,
    make_test_client,
)


@pytest.fixture()
def source_client(referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock) -> TestClient:
    return make_test_client(referral_service, crypto_client, make_auth_context())


# ---------------------------------------------------------------------------
# POST /v1/registrations
# ---------------------------------------------------------------------------


class TestCreateRegistration:
    def test_creates_registration(self, source_client: TestClient) -> None:
        response = source_client.post(
            "/v1/registrations",
            json={"pseudonym": "pseu", "oprf_key": "key1"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["ura"] == TEST_URA
        assert body["source_id"] == TEST_SOURCE_ID
        assert body["care_context"] is None
        assert "created_at" in body

    def test_creates_registration_with_care_context(self, source_client: TestClient) -> None:
        response = source_client.post(
            "/v1/registrations",
            json={"pseudonym": "pseu", "oprf_key": "key1", "care_context": "Hospital"},
        )
        assert response.status_code == 201
        assert response.json()["care_context"] == "Hospital"

    def test_conflict_on_duplicate(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        response = source_client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 409

    def test_requires_create_scope(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        client = make_test_client(referral_service, crypto_client, ctx)
        response = client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 403

    def test_requires_source_role(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(role=AuthorizationRole.CONSULTING, scopes=[AuthorizationScope.CREATE])
        client = make_test_client(referral_service, crypto_client, ctx)
        response = client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 403

    def test_requires_source_id_in_claims(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(source_id=None, scopes=[AuthorizationScope.CREATE])
        client = make_test_client(referral_service, crypto_client, ctx)
        response = client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /v1/registrations
# ---------------------------------------------------------------------------


class TestGetRegistrations:
    def test_returns_empty_list(self, source_client: TestClient) -> None:
        response = source_client.get("/v1/registrations")
        assert response.status_code == 200
        body = response.json()
        assert body["registrations"] == []
        assert body["total"] == 0

    def test_returns_own_registrations(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        response = source_client.get("/v1/registrations")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["registrations"][0]["ura"] == TEST_URA

    def test_filters_by_pseudonym(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "p1", "oprf_key": "k"})
        source_client.post("/v1/registrations", json={"pseudonym": "p2", "oprf_key": "k"})

        # p1:k is what the mock returns for pseudonym=p1, oprf_key=k
        response = source_client.get("/v1/registrations", params={"pseudonym": "p1", "oprf_key": "k"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_filters_by_care_context(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "p1", "oprf_key": "k", "care_context": "Hospital"})
        source_client.post("/v1/registrations", json={"pseudonym": "p2", "oprf_key": "k", "care_context": "Clinic"})

        response = source_client.get("/v1/registrations", params={"care_context": "Hospital"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["registrations"][0]["care_context"] == "Hospital"

    def test_does_not_return_other_ura_registrations(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx_a = make_auth_context(ura="00000001", source_id="src-a")
        ctx_b = make_auth_context(ura="00000002", source_id="src-b")
        client_a = make_test_client(referral_service, crypto_client, ctx_a)
        client_b = make_test_client(referral_service, crypto_client, ctx_b)

        client_a.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})

        response = client_b.get("/v1/registrations")
        assert response.json()["total"] == 0

    def test_requires_read_scope(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.CREATE])
        client = make_test_client(referral_service, crypto_client, ctx)
        assert client.get("/v1/registrations").status_code == 403

    def test_requires_source_role(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(role=AuthorizationRole.CONSULTING, scopes=[AuthorizationScope.READ])
        client = make_test_client(referral_service, crypto_client, ctx)
        assert client.get("/v1/registrations").status_code == 403


# ---------------------------------------------------------------------------
# DELETE /v1/registrations
# ---------------------------------------------------------------------------


class TestDeleteRegistrations:
    def test_deletes_all_own_registrations(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "p1", "oprf_key": "k"})
        source_client.post("/v1/registrations", json={"pseudonym": "p2", "oprf_key": "k"})

        response = source_client.delete("/v1/registrations")
        assert response.status_code == 204

        assert source_client.get("/v1/registrations").json()["total"] == 0

    def test_deletes_by_pseudonym_filter(self, source_client: TestClient) -> None:
        source_client.post("/v1/registrations", json={"pseudonym": "p1", "oprf_key": "k"})
        source_client.post("/v1/registrations", json={"pseudonym": "p2", "oprf_key": "k"})

        source_client.delete("/v1/registrations", params={"pseudonym": "p1", "oprf_key": "k"})

        assert source_client.get("/v1/registrations").json()["total"] == 1

    def test_does_not_delete_other_ura_registrations(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx_a = make_auth_context(ura="00000001", source_id="src-a")
        ctx_b = make_auth_context(ura="00000002", source_id="src-b")
        client_a = make_test_client(referral_service, crypto_client, ctx_a)
        client_b = make_test_client(referral_service, crypto_client, ctx_b)

        client_a.post("/v1/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        client_b.delete("/v1/registrations")

        assert client_a.get("/v1/registrations").json()["total"] == 1

    def test_requires_delete_scope(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        client = make_test_client(referral_service, crypto_client, ctx)
        assert client.delete("/v1/registrations").status_code == 403

    def test_requires_source_role(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(role=AuthorizationRole.CONSULTING, scopes=[AuthorizationScope.DELETE])
        client = make_test_client(referral_service, crypto_client, ctx)
        assert client.delete("/v1/registrations").status_code == 403

    def test_requires_source_id_in_claims(
        self, referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock
    ) -> None:
        ctx = make_auth_context(source_id=None, scopes=[AuthorizationScope.DELETE])
        client = make_test_client(referral_service, crypto_client, ctx)
        assert client.delete("/v1/registrations").status_code == 403
