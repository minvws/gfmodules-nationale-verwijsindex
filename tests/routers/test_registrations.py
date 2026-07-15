import pytest
from fastapi.testclient import TestClient

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.auth.data import AuthorizationScope
from app.services.exceptions import InvalidKeyInfoError
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.routers.conftest import (
    TEST_SOURCE_ID,
    TEST_URA,
    make_auth_context,
    make_test_client,
)


@pytest.fixture()
def source_client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
) -> TestClient:
    return make_test_client(referral_service, crypto_client, key_info_service, make_auth_context())


# ---------------------------------------------------------------------------
# POST /registrations
# ---------------------------------------------------------------------------


class TestCreateRegistration:
    def test_creates_registration(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", mechanism="AES_CBC")

        response = source_client.post(
            "/registrations",
            json={"pseudonym": "pseu", "oprf_key": "key1"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ura_number"] == TEST_URA
        assert body["source_id"] == TEST_SOURCE_ID
        assert "created_at" in body

    def test_creates_should_raise_when_no_key_registerd(self, source_client: TestClient) -> None:
        with pytest.raises(InvalidKeyInfoError):
            source_client.post(
                "/registrations",
                json={"pseudonym": "pseu", "oprf_key": "key1"},
            )

    def test_requires_create_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        client = make_test_client(referral_service, crypto_client, key_info_service, ctx)
        response = client.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 403

    def test_requires_source_id_in_claims(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        ctx = make_auth_context(source_id=None, scopes=[AuthorizationScope.CREATE])
        client = make_test_client(referral_service, crypto_client, key_info_service, ctx)
        response = client.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "key1"})
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /registrations
# ---------------------------------------------------------------------------


class TestGetRegistrations:
    def test_returns_empty_list(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("label-1", "AES_CBC")
        response = source_client.get("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 200
        body = response.json()
        assert body["registrations"] == []
        assert body["total"] == 0

    def test_returns_own_registrations(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        source_client.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        response = source_client.get("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["registrations"][0]["ura_number"] == TEST_URA

    def test_filters_by_pseudonym(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        source_client.post("/registrations", json={"pseudonym": "p1", "oprf_key": "k"})
        source_client.post("/registrations", json={"pseudonym": "p2", "oprf_key": "k"})

        response = source_client.get("/registrations", params={"pseudonym": "p1", "oprf_key": "k"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_does_not_return_other_ura_registrations(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        ctx_a = make_auth_context(ura="00000001", source_id="src-a")
        ctx_b = make_auth_context(ura="00000002", source_id="src-b")
        client_a = make_test_client(referral_service, crypto_client, key_info_service, ctx_a)
        client_b = make_test_client(referral_service, crypto_client, key_info_service, ctx_b)

        client_a.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})

        response = client_b.get("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.json()["total"] == 0

    def test_requires_read_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.CREATE])
        client = make_test_client(referral_service, crypto_client, key_info_service, ctx)

        assert client.get("/registrations", params={"pseudonym": "p", "oprf_key": "k"}).status_code == 403


# ---------------------------------------------------------------------------
# DELETE /registrations
# ---------------------------------------------------------------------------


class TestDeleteRegistrations:
    def test_deletes_registration(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        source_client.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        response = source_client.delete("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 204

        remaining = source_client.get("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})
        assert remaining.json()["total"] == 0

    def test_deletes_only_matching_pseudonym(self, source_client: TestClient, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        source_client.post("/registrations", json={"pseudonym": "p1", "oprf_key": "k"})
        source_client.post("/registrations", json={"pseudonym": "p2", "oprf_key": "k"})

        source_client.delete("/registrations", params={"pseudonym": "p1", "oprf_key": "k"})

        assert source_client.get("/registrations", params={"pseudonym": "p1", "oprf_key": "k"}).json()["total"] == 0
        assert source_client.get("/registrations", params={"pseudonym": "p2", "oprf_key": "k"}).json()["total"] == 1

    def test_does_not_delete_other_ura_registrations(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        ctx_a = make_auth_context(ura="00000001", source_id="src-a")
        ctx_b = make_auth_context(ura="00000002", source_id="src-b")
        client_a = make_test_client(referral_service, crypto_client, key_info_service, ctx_a)
        client_b = make_test_client(referral_service, crypto_client, key_info_service, ctx_b)

        client_a.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        client_b.delete("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"})

        assert client_a.get("/registrations", params={"pseudonym": "pseu", "oprf_key": "k"}).json()["total"] == 1

    def test_requires_delete_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        client = make_test_client(referral_service, crypto_client, key_info_service, ctx)
        assert client.delete("/registrations", params={"pseudonym": "p", "oprf_key": "k"}).status_code == 403

    def test_requires_source_id_in_claims(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
        key_info_service: KeyInfoService,
    ) -> None:
        ctx = make_auth_context(source_id=None, scopes=[AuthorizationScope.DELETE])
        client = make_test_client(referral_service, crypto_client, key_info_service, ctx)
        assert client.delete("/registrations", params={"pseudonym": "p", "oprf_key": "k"}).status_code == 400
