import random
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.data import UraNumber
from app.db.db import Database
from app.db.models.ura_number_whitelist import UraNumberWhitelistEntity
from app.middleware.ura_middleware.request_ura_middleware import RequestUraMiddleware
from app.middleware.ura_middleware.whitelisted_ura_middleware import WhitelistedUraMiddleware


@pytest.fixture()
def request_ura_middleware_mock(mocker: MockerFixture) -> Any:
    return mocker.Mock(spec=RequestUraMiddleware)


@pytest.fixture()
def whitelisted_ura_middleware(
    database: Database, request_ura_middleware_mock: RequestUraMiddleware
) -> WhitelistedUraMiddleware:
    return WhitelistedUraMiddleware(
        db=database, ura_middleware=request_ura_middleware_mock, whitelist_cache_in_seconds=30
    )


def test_whitelist(whitelisted_ura_middleware: WhitelistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberWhitelistEntity(ura_number))
        session.commit()
    actual = whitelisted_ura_middleware.whitelist
    assert actual == [ura_number]


def test_validate(whitelisted_ura_middleware: WhitelistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberWhitelistEntity(ura_number))
        session.commit()

    whitelisted_ura_middleware._validate(ura_number)


def test_validate_raises_unauthorized(whitelisted_ura_middleware: WhitelistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(1, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberWhitelistEntity(ura_number))
        session.commit()

    with pytest.raises(HTTPException):
        whitelisted_ura_middleware._validate(UraNumber(int(str(ura_number)) - 1))


def test_authenticated_ura_calls_middleware(
    whitelisted_ura_middleware: WhitelistedUraMiddleware,
    request_ura_middleware_mock: Mock,
    database: Database,
    mocker: MockerFixture,
) -> None:
    expected = UraNumber(random.randint(0, 99999999))

    with database.get_db_session() as session:
        session.add(UraNumberWhitelistEntity(expected))
        session.commit()

    request_ura_middleware_mock.authenticated_ura.return_value = expected

    request = mocker.MagicMock(spec=Request)
    actual = whitelisted_ura_middleware.authenticated_ura(request)

    assert actual == expected

    request_ura_middleware_mock.authenticated_ura.assert_called_once_with(request)
