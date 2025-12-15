import random
import time
from unittest import mock

import pytest
from pytest_mock import MockerFixture
from starlette.exceptions import HTTPException

from app.db.db import Database
from app.db.models.ura_number_allowlist import UraNumberAllowlistEntity
from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.models.ura import UraNumber


@pytest.fixture()
def allowlisted_ura_middleware(
    database: Database,
) -> AllowlistedUraMiddleware:
    return AllowlistedUraMiddleware(
        db=database,
        allowlist_cache_in_seconds=30,
    )


def test_allowlist(allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(0, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number))
        session.commit()
    actual = allowlisted_ura_middleware.allowlist
    assert actual == [ura_number]


def test_expire_allowlist(
    allowlisted_ura_middleware: AllowlistedUraMiddleware,
    database: Database,
    mocker: MockerFixture,
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

    allowlisted_ura_middleware.filter(ura_number)


def test_validate_raises_unauthorized(allowlisted_ura_middleware: AllowlistedUraMiddleware, database: Database) -> None:
    ura_number = UraNumber(random.randint(1, 99999999))
    with database.get_db_session() as session:
        session.add(UraNumberAllowlistEntity(ura_number))
        session.commit()

    with pytest.raises(HTTPException):
        allowlisted_ura_middleware.filter(UraNumber(int(str(ura_number)) - 1))
