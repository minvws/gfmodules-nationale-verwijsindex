from collections.abc import Generator
from typing import Any

import pytest

from app.config import ConfigDatabase
from app.db.db import Database


@pytest.fixture()
def database() -> Generator[Database, Any, None]:
    config_database = ConfigDatabase(dsn="sqlite:///:memory:", retry_backoff=[])
    try:
        db = Database(config_database=config_database)
        db.generate_tables()
        yield db
    except Exception as e:
        raise e
