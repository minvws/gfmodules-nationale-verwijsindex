import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any, Final

import pytest
from cryptography.x509 import Certificate

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.models.ura import UraNumber
from app.services.auth.header import AuthHeaderService
from app.services.http import HttpService
from app.services.referral_service import ReferralService
from app.utils.certificates.utils import (
    load_certificate,
    load_one_certificate_file,
)
from tests.test_config import get_test_config

TEST_SCRIPT_PATH: Final[str] = "tools/generate_test_certs.sh"
TEST_CERTIFICATE_PATH: Final[str] = "tests/secrets/mock-server-cert.crt"
TEST_CERTIFICATE_DIR: Final[str] = "tests/secrets/"


@pytest.fixture()
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


@pytest.fixture()
def mock_referral_entity() -> ReferralEntity:
    return ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        source="Some-Device",
        organization_type="Hospital",
    )


@pytest.fixture()
def referral_service(database: Database) -> ReferralService:
    return ReferralService(database=database)


@pytest.fixture()
def auth_header_service() -> AuthHeaderService:
    config = get_test_config()
    return AuthHeaderService(config=config.oauth)


@pytest.fixture(scope="session")
def certificate_str(ura_number: UraNumber) -> str:
    global TEST_SCRIPT_PATH
    global TEST_CERTIFICATE_PATH
    root = Path(__file__).parent.parent
    path = os.path.join(str(root) + "/" + TEST_SCRIPT_PATH)
    exit_code = subprocess.call(f"{path} {str(ura_number)}", shell=True)
    if exit_code != 0:
        raise Exception(f"script {TEST_SCRIPT_PATH} exited with error code: {exit_code}")

    return load_one_certificate_file(TEST_CERTIFICATE_PATH)


@pytest.fixture()
def certificate() -> Certificate:
    global TEST_CERTIFICATE_PATH
    return load_certificate(TEST_CERTIFICATE_PATH)


@pytest.fixture()
def cert_path() -> str:
    global TEST_CERTIFICATE_PATH
    path = TEST_CERTIFICATE_PATH

    return path


@pytest.fixture()
def cert_dir() -> str:
    global TEST_CERTIFICATE_DIR
    dir = TEST_CERTIFICATE_DIR
    return dir
