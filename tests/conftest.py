import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any, Final

import pytest
from cryptography.x509 import Certificate

from app.config import ConfigDatabase
from app.db.db import Database
from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.models.ura import UraNumber
from app.services.authorization_services.stub import StubAuthService
from app.services.http import HttpService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.utils.certificates.utils import load_certificate
from tests.test_config import get_test_config

TEST_SCRIPT_PATH: Final[str] = "tools/generate_test_certs.sh"
TEST_CERTIFICATE_PATH: Final[str] = "tests/secrets/mock-server-cert.crt"
TEST_CERTIFICATE_DIR: Final[str] = "tests/secrets/"


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    try:
        db = Database(config_database=config_database)
        db.generate_tables()
        yield db
    except Exception as e:
        raise e


@pytest.fixture()
def http_service() -> HttpService:
    config = get_test_config()
    return HttpService(**config.pseudonym_api.model_dump())


@pytest.fixture(scope="session")
def ura_number() -> UraNumber:
    return UraNumber("00000123")


@pytest.fixture()
def ura_filter_service(database: Database) -> AllowlistedUraMiddleware:
    return AllowlistedUraMiddleware(database, 10)


@pytest.fixture()
def prs_registration_service(ura_number: UraNumber) -> PrsRegistrationService:
    config = get_test_config()
    return PrsRegistrationService(config=config.pseudonym_api, ura_number=ura_number)


@pytest.fixture()
def referral_service(database: Database) -> ReferralService:
    return ReferralService(database=database, auth_service=StubAuthService())  # type: ignore


@pytest.fixture(scope="session")
def certificate_str(ura_number: UraNumber) -> str:
    global TEST_SCRIPT_PATH
    global TEST_CERTIFICATE_PATH
    root = Path(__file__).parent.parent
    path = os.path.join(str(root) + "/" + TEST_SCRIPT_PATH)
    exit_code = subprocess.call(f"{path} {str(ura_number)}", shell=True)
    if exit_code != 0:
        raise Exception(f"script {TEST_SCRIPT_PATH} exited with error code: {exit_code}")

    with open(TEST_CERTIFICATE_PATH, "r") as f:
        data = f.read()

    return data


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
