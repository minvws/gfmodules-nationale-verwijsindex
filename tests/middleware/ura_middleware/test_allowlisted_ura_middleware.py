import random
import time
from typing import Any
from unittest import mock
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.data import UraNumber
from app.db.db import Database
from app.db.models.ura_number_allowlist import UraNumberAllowlistEntity
from app.middleware.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura_middleware.request_ura_middleware import RequestUraMiddleware


@pytest.fixture()
def request_ura_middleware_mock(mocker: MockerFixture) -> Any:
    return mocker.Mock(spec=RequestUraMiddleware)


@pytest.fixture()
def allowlisted_ura_middleware(
    database: Database, request_ura_middleware_mock: RequestUraMiddleware
) -> AllowlistedUraMiddleware:
    return AllowlistedUraMiddleware(
        db=database, ura_middleware=request_ura_middleware_mock, allowlist_cache_in_seconds=30
    )


def test_allowlist(allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number))
        session.commit()
    actual = allowlisted_ura_middleware.allowlist
    assert actual == [ura_number]


def test_expire_allowlist(
    allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database, mocker: MockerFixture
) -> None:
    start_time = time.time()
    assert allowlisted_ura_middleware.allowlist == []

    ura_number_1 = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number_1))
        session.commit()

    assert allowlisted_ura_middleware.allowlist == []
    mocker.patch("time.time", mock.Mock(return_value=start_time + 31))
    assert allowlisted_ura_middleware.allowlist == [ura_number_1]

    ura_number_2 = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number_2))
        session.commit()

    assert allowlisted_ura_middleware.allowlist == [ura_number_1]
    mocker.patch("time.time", mock.Mock(return_value=start_time + 62))
    assert allowlisted_ura_middleware.allowlist == [ura_number_1, ura_number_2]


def test_validate(allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number))
        session.commit()

    allowlisted_ura_middleware._validate(ura_number)


def test_validate_raises_unauthorized(allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(1, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number))
        session.commit()

    with pytest.raises(HTTPException):
        allowlisted_ura_middleware._validate(UraNumber(int(str(ura_number)) - 1))


def test_authenticated_ura_calls_middleware(
    allowlisted_ura_middleware: AllowlistedUraMiddleware,
    request_ura_middleware_mock: Mock,
    database: Database,
    mocker: MockerFixture,
) -> None:
    expected = UraNumber(random.randint(0, 99999999))

    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(expected, "description"))
        session.commit()

    request_ura_middleware_mock.authenticated_ura.return_value = expected

    request = mocker.MagicMock(spec=Request)
    actual = allowlisted_ura_middleware.authenticated_ura(request)

    assert actual == expected

    request_ura_middleware_mock.authenticated_ura.assert_called_once_with(request)
