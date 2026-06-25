from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import DataError, OperationalError

from app.db.session import DbSession
from app.logging.events import Log


def _operational_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("server closed the connection unexpectedly"))


def test_retry_emits_db_connection_failed_on_operational_error(mocker: MockerFixture) -> None:
    mocker.patch("app.db.session.sleep")
    log_event = mocker.patch("app.db.session.Log.event")
    session = DbSession(engine=MagicMock(), retry_backoff=[0.5])

    attempts = {"n": 0}

    def op() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _operational_error()
        return "ok"

    assert session._retry(op) == "ok"

    log_event.assert_called_once()
    args, kwargs = log_event.call_args
    assert args[1] is Log.DB_CONNECTION_FAILED
    assert kwargs["error_type"] == "OperationalError"
    assert kwargs["retry_attempt"] == 1
    assert kwargs["backoff_seconds"] == 0.5


def test_retry_emits_db_connection_failed_per_attempt(mocker: MockerFixture) -> None:
    mocker.patch("app.db.session.sleep")
    log_event = mocker.patch("app.db.session.Log.event")
    session = DbSession(engine=MagicMock(), retry_backoff=[0.1, 0.2])

    attempts = {"n": 0}

    def op() -> str:
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise _operational_error()
        return "ok"

    assert session._retry(op) == "ok"

    assert log_event.call_count == 2
    assert [c.kwargs["retry_attempt"] for c in log_event.call_args_list] == [1, 2]
    assert [c.kwargs["backoff_seconds"] for c in log_event.call_args_list] == [0.1, 0.2]


def test_retry_emits_db_schema_error_on_data_error_and_reraises(mocker: MockerFixture) -> None:
    log_event = mocker.patch("app.db.session.Log.event")
    session = DbSession(engine=MagicMock(), retry_backoff=[])

    def op() -> str:
        raise DataError(
            "INSERT ...",
            {"pseudonym": "ABCDEFGHIJK"},
            Exception("value too long for type character varying(8)"),
        )

    with pytest.raises(DataError):
        session._retry(op)

    log_event.assert_called_once()
    args, kwargs = log_event.call_args
    assert args[1] is Log.DB_SCHEMA_ERROR
    assert kwargs["exception_type"] == "DataError"
    assert kwargs["value_length"] == 11
    assert kwargs["column_limit"] == 8
