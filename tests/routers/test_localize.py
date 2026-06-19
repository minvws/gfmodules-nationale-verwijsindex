import pytest
from fastapi.testclient import TestClient

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber
from app.services.referral_service import ReferralService
from tests.routers.conftest import (
    TEST_OIN,
    TEST_URA,
    make_auth_context,
    make_localize_auth_context,
    make_test_client,
)


@pytest.fixture()
def localize_client(referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock) -> TestClient:
    return make_test_client(referral_service, crypto_client, make_localize_auth_context())


@pytest.fixture()
def source_client(referral_service: ReferralService, crypto_client: CryptoServiceApiClientMock) -> TestClient:
    """Client with SOURCE role for seeding registrations."""
    return make_test_client(referral_service, crypto_client, make_auth_context(source_id="SRC-001"))


class TestLocalize:
    def test_returns_empty_when_no_registrations(self, localize_client: TestClient) -> None:
        response = localize_client.post(
            "/localize",
            json={"pseudonym": "pseu", "oprf_key": "k"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_matching_registrations(
        self,
        localize_client: TestClient,
        source_client: TestClient,
    ) -> None:
        source_client.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})

        response = localize_client.post("/localize", json={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["ura_number"] == TEST_URA
        assert results[0]["source_id"] == "SRC-001"

    def test_returns_multiple_ura_results(
        self,
        localize_client: TestClient,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
    ) -> None:
        client_a = make_test_client(
            referral_service,
            crypto_client,
            make_auth_context(ura="00000001", source_id="src-a"),
        )
        client_b = make_test_client(
            referral_service,
            crypto_client,
            make_auth_context(ura="00000002", source_id="src-b"),
        )

        client_a.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})
        client_b.post("/registrations", json={"pseudonym": "pseu", "oprf_key": "k"})

        response = localize_client.post("/localize", json={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_requires_localize_scope(
        self,
        referral_service: ReferralService,
        crypto_client: CryptoServiceApiClientMock,
    ) -> None:
        ctx_wrong_scope = AuthContext(
            claims=AuthenticationClaims(ura_number=UraNumber(TEST_URA), oin=TEST_OIN, source_id=None),
            scope=[AuthorizationScope.READ],
            audience="nvi.service",
        )
        client = make_test_client(referral_service, crypto_client, ctx_wrong_scope)
        response = client.post("/localize", json={"pseudonym": "pseu", "oprf_key": "k"})
        assert response.status_code == 403
