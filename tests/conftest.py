from collections.abc import Generator
from typing import Any

import pytest

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.key_info import KeyInfoEntity
from app.db.models.referral import ReferralEntity
from app.db.repository.key_info_repository import KeyInfoRepository
from app.db.repository.referral_repository import ReferralRepository
from app.models.ura import UraNumber
from app.services.auth.header import AuthHeaderService
from app.services.http import HttpService
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.test_config import get_test_config


@pytest.fixture(autouse=True)
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    try:
        yield db
    finally:
        db.engine.dispose()


@pytest.fixture()
def referral_repository(database: Database) -> ReferralRepository:
    return ReferralRepository(db_session=database.get_db_session())


@pytest.fixture()
def key_info_repository(database: Database) -> KeyInfoRepository:
    return KeyInfoRepository(db_session=database.get_db_session())


@pytest.fixture()
def http_service() -> HttpService:
    config = get_test_config()
    return HttpService(
        endpoint=config.crypto_service_api.endpoint,
        timeout=config.crypto_service_api.timeout,
        mtls_cert=config.crypto_service_api.mtls_cert,
        mtls_key=config.crypto_service_api.mtls_key,
        verify_ca=config.crypto_service_api.verify_ca,
    )


@pytest.fixture(scope="session")
def ura_number() -> UraNumber:
    return UraNumber("00000123")


@pytest.fixture
def mock_key_info() -> KeyInfoEntity:
    return KeyInfoEntity(label="label-1", mechanism="AES_CBC", active=True)


@pytest.fixture()
def mock_referral_entity() -> ReferralEntity:
    return ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        source="Some-Device",
    )


@pytest.fixture()
def referral_service(database: Database) -> ReferralService:
    return ReferralService(database=database)


@pytest.fixture()
def key_info_service(database: Database) -> KeyInfoService:
    return KeyInfoService(database)


@pytest.fixture()
def auth_header_service() -> AuthHeaderService:
    config = get_test_config()
    return AuthHeaderService(expected_audiences=config.authorization_headers.expected_audiences)
