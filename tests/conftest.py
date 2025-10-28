from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.config import ConfigDatabase
from app.db.db import Database
from app.services.api_service import HttpService
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.lmr_service import LmrService
from app.services.entity.logging_entity_service import LoggingEntityService
from app.services.entity.referral_entity_service import ReferralEntityService
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    db = Database(config_database=config_database)
    db.generate_tables()
    yield db


@pytest.fixture()
def referral_entity_service(database: Database) -> ReferralEntityService:
    return ReferralEntityService(database=database)


@pytest.fixture()
@patch("app.services.pseudonym_service.PseudonymService.register_nvi_at_prs")
def prs_service(mock_register_nvi: MagicMock) -> PseudonymService:
    mock_register_nvi.return_value = None
    return PseudonymService(
        mtls_cert="fake_cert",
        decrypt_service=MagicMock(),
        api_service=MagicMock(spec=HttpService),
    )


@pytest.fixture()
def logging_entity_service(database: Database) -> LoggingEntityService:
    return LoggingEntityService(database=database)


@pytest.fixture()
def lmr_service() -> BaseAuthService:
    return LmrService(api_service=MagicMock(spec=HttpService))


@pytest.fixture()
def referral_service() -> ReferralService:
    return ReferralService(
        entity_service=MagicMock(spec=ReferralEntityService),
        prs_service=MagicMock(spec=PseudonymService),
        audit_logger=MagicMock(spec=LoggingEntityService),
        auth_service=MagicMock(spec=BaseAuthService),
    )
