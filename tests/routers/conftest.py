from typing import Any, Generator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.auth import get_auth_ctx
from app.config import ConfigDatabase, set_config
from app.db.db import Database
from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.dependencies import (
    get_crypto_service_api_client,
    get_key_info_service,
    get_referral_service,
)
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.test_config import get_test_config

TEST_URA = "00000001"
TEST_SOURCE_ID = "SRC-001"
TEST_OIN = "00000000000000000001"
TEST_ORG_NAME = "Test Organization"


def make_auth_context(
    ura: str = TEST_URA,
    source_id: str | None = TEST_SOURCE_ID,
    scopes: list[AuthorizationScope] | None = None,
) -> AuthContext:
    if scopes is None:
        scopes = [
            AuthorizationScope.CREATE,
            AuthorizationScope.READ,
            AuthorizationScope.DELETE,
        ]
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=UraNumber(ura),
            organization_name=TEST_ORG_NAME,
            source_id=source_id,
            oin=TEST_OIN,
        ),
        scope=scopes,
        audience="nvi.service",
    )


def make_localize_auth_context(ura: str = TEST_URA) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=UraNumber(ura),
            organization_name=TEST_ORG_NAME,
            source_id=None,
            oin=TEST_OIN,
        ),
        scope=[AuthorizationScope.LOCALIZE],
        audience="nvi.service",
    )


@pytest.fixture()
def db() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    try:
        yield db
    finally:
        db.engine.dispose()


@pytest.fixture()
def referral_service(db: Database) -> ReferralService:
    return ReferralService(database=db)


@pytest.fixture()
def crypto_client() -> CryptoServiceApiClientMock:
    return CryptoServiceApiClientMock()


@pytest.fixture()
def key_info_service(db: Database) -> KeyInfoService:
    return KeyInfoService(db)


def make_test_client(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
    auth_context: AuthContext,
) -> TestClient:
    set_config(get_test_config())
    app = setup_fastapi()

    app.dependency_overrides[get_referral_service] = lambda: referral_service
    app.dependency_overrides[get_crypto_service_api_client] = lambda: crypto_client
    app.dependency_overrides[get_key_info_service] = lambda: key_info_service

    def override_auth_ctx(request: Request) -> AuthContext:
        request.state.auth = auth_context
        return auth_context

    app.dependency_overrides[get_auth_ctx] = override_auth_ctx

    return TestClient(app, raise_server_exceptions=True)
