from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.data import UraNumber
from app.data_models.logging import ReferralLoggingPayload, ReferralRequestType
from app.db.models.referral_request_log import ReferralRequestLogEntry
from app.services.entity.logging_entity_service import LoggingEntityService


@pytest.fixture()
def mock_entry() -> ReferralLoggingPayload:
    return ReferralLoggingPayload(
        endpoint="https://example.com/",
        requesting_uzi_number="test_uzi_number",
        requesting_ura_number=UraNumber("1234"),
        request_type=ReferralRequestType.CREATE,
        payload={"data": "test"},
    )


def test_audit_logging_service_log_succeeds(
    mock_entry: ReferralLoggingPayload,
    logging_entity_service: LoggingEntityService,
) -> None:
    logging_entity_service.log(mock_entry)

    with logging_entity_service.database.get_db_session() as session:
        stmt = select(ReferralRequestLogEntry)
        result = session.execute(stmt)
        logged_entries = result.scalars().all()

        assert len(logged_entries) == 1

        logged_entry = logged_entries[0]

        assert logged_entry.endpoint == mock_entry.endpoint
        assert logged_entry.requesting_uzi_number == mock_entry.requesting_uzi_number
        assert logged_entry.ura_number == str(mock_entry.requesting_ura_number)
        assert logged_entry.request_type == mock_entry.request_type
        assert logged_entry.payload == mock_entry.payload


@patch("app.db.repository.referral_request_logging_repository.ReferralRequestLoggingRepository.add_one")
@patch("app.services.entity.logging_entity_service.logger")
def test_audit_logging_service_log_fails(
    mock_logger: MagicMock,
    mock_add_one: MagicMock,
    mock_entry: ReferralLoggingPayload,
    logging_entity_service: LoggingEntityService,
) -> None:
    mock_add_one.side_effect = Exception("Database error")

    logging_entity_service.log(mock_entry)

    mock_logger.error.assert_called_once_with("Failed to log referral: Database error")

    with logging_entity_service.database.get_db_session() as session:
        stmt = select(ReferralRequestLogEntry)
        result = session.execute(stmt)
        logged_entries = result.scalars().all()

        assert len(logged_entries) == 0
