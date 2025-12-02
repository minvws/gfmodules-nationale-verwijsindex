from collections.abc import Generator
from typing import Any

import pytest

from app.config import ConfigDatabase
from app.db.db import Database
from app.models.ura import UraNumber
from app.services.authorization_services.stub import StubAuthService
from app.services.http import HttpService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.ura.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from tests.test_config import get_test_config


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


@pytest.fixture()
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
