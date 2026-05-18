import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.auth import get_auth_ctx
from app.config import ConfigDatabase
from app.db.db import Database
from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.dependencies import get_crypto_service_api_client, get_referral_service
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationRole, AuthorizationScope
from app.models.ura import UraNumber
from app.services.referral_service import ReferralService

TEST_URA = "00000001"
TEST_SOURCE_ID = "SRC-001"
TEST_OIN = "00000000000000000001"


def make_auth_context(
    ura: str = TEST_URA,
    source_id: str | None = TEST_SOURCE_ID,
    scopes: list[AuthorizationScope] | None = None,
    role: AuthorizationRole | None = AuthorizationRole.SOURCE,
) -> AuthContext:
    if scopes is None:
        scopes = [AuthorizationScope.CREATE, AuthorizationScope.READ, AuthorizationScope.DELETE]
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=UraNumber(ura),
            source_id=source_id,
            oin=TEST_OIN,
        ),
        scope=scopes,
        audience="nvi.service",
        role=role,
    )


def make_localize_auth_context(ura: str = TEST_URA) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=UraNumber(ura),
            source_id=None,
            oin=TEST_OIN,
        ),
        scope=[AuthorizationScope.LOCALIZE],
        audience="nvi.service",
        role=AuthorizationRole.CONSULTING,
    )


@pytest.fixture()
def db() -> Database:
    config = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    database = Database(config_database=config)
    database.generate_tables()
    return database


@pytest.fixture()
def referral_service(db: Database) -> ReferralService:
    return ReferralService(database=db)


@pytest.fixture()
def crypto_client() -> CryptoServiceApiClientMock:
    return CryptoServiceApiClientMock()


def make_test_client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    auth_context: AuthContext,
) -> TestClient:
    app = setup_fastapi()

    app.dependency_overrides[get_referral_service] = lambda: referral_service
    app.dependency_overrides[get_crypto_service_api_client] = lambda: crypto_client

    def override_auth_ctx(request: Request) -> AuthContext:
        request.state.auth = auth_context
        return auth_context

    app.dependency_overrides[get_auth_ctx] = override_auth_ctx

    return TestClient(app, raise_server_exceptions=True)
