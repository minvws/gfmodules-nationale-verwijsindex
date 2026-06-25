import logging
import random
import re
from time import sleep
from typing import Any, Callable, List, ParamSpec, Tuple, Type, TypeVar

from sqlalchemy import Delete, Engine, Insert, Result
from sqlalchemy.exc import DatabaseError, DataError, OperationalError, PendingRollbackError
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import TypedReturnsRows

from app.db.models.base import Base
from app.db.repository import respository_base
from app.logging.events import Log

_VARCHAR_LIMIT_RE = re.compile(r"character varying\((\d+)\)")


def _value_length_from_params(params: Any) -> int | None:
    """
    Infer the longest payload length from SQL params for logging.
    """
    if params is None:
        return None

    if isinstance(params, dict):
        values = params.values()
    elif isinstance(params, (list, tuple, set)):
        values = params  # type: ignore
    else:
        values = (params,)  # type: ignore

    lengths = [len(value) for value in values if isinstance(value, (str, bytes, bytearray))]
    return max(lengths) if lengths else None


def _schema_error_fields(exc: DataError) -> dict[str, Any]:
    """
    Extract schema diagnostics from a DataError.
    """
    fields: dict[str, Any] = {
        "exception_type": type(exc).__name__,
        "value_length": _value_length_from_params(getattr(exc, "params", None)),
    }
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    if diag is not None:
        if getattr(diag, "table_name", None):
            fields["table"] = diag.table_name
        if getattr(diag, "column_name", None):
            fields["column"] = diag.column_name
    match = _VARCHAR_LIMIT_RE.search(str(getattr(exc, "orig", exc)))
    if match:
        fields["column_limit"] = int(match.group(1))
    return fields


"""
This module contains the DbSession class, which is a context manager that provides a session to interact with
the database. It also provides methods to add and delete resources from the session, and to commit or rollback the
current transaction.

Usage:

    with DbSession(engine, config) as session:
        repo = session.get_repository(MyModelRepository)
        repo.find_all()
        session.add_resource(MyModel())
        session.commit()
"""


"""
This module contains the DbSession class, which is a context manager that provides a session to interact with
the database. It also provides methods to add and delete resources from the session, and to commit or rollback the
current transaction.

Usage:

    with DbSession(engine, config) as session:
        repo = session.get_repository(MyModel)
        repo.find_all()
        session.add(MyModel())
        session.commit()
"""

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R", bound=Tuple[Any, ...])


class DbSession:
    _engine: Engine
    _retry_backoff: List[float]

    def __init__(self, engine: Engine, retry_backoff: List[float]) -> None:
        self._engine = engine
        self._retry_backoff = retry_backoff

    def __enter__(self) -> "DbSession":
        """
        Create a new session when entering the context manager
        """
        self.session = Session(self._engine, expire_on_commit=False)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Close the session when exiting the context manager
        """
        self.session.close()

    def get_repository(
        self, repository_class: Type["respository_base.TRepositoryBase"]
    ) -> "respository_base.TRepositoryBase":
        """
        Returns an instantiated repository for the given model class
        """
        if issubclass(repository_class, respository_base.RepositoryBase):
            return repository_class(self)
        raise ValueError(f"No repository registered for model {repository_class}")

    def add(self, entry: Base) -> None:
        """
        Add a resource to the session, so it will be inserted/updated in the database on the next commit

        :param entry:
        :return:
        """
        self._retry(self.session.add, entry)

    def delete(self, entry: Base) -> None:
        """
        Delete a resource from the session, so it will be deleted from the database on the next commit

        :param entry:
        :return:
        """
        # database cascading will take care of the rest
        self._retry(self.session.delete, entry)

    def commit(self) -> None:
        """
        Commits any pending work in the session to the database

        :return:
        """
        self._retry(self.session.commit)

    def rollback(self) -> None:
        """
        Rollback the current transaction

        :return:
        """
        self._retry(self.session.rollback)

    def delete_stmt(self, stmt: Delete) -> Result[R]:
        """
        Execute a statement in the current session

        :param stmt:
        :return:
        """
        return self._retry(self.session.execute, stmt)

    def execute(self, stmt: TypedReturnsRows[R] | Insert) -> Result[R]:
        """
        Execute a statement in the current session

        :param stmt:
        :return:
        """
        return self._retry(self.session.execute, stmt)

    def begin(self) -> Any:
        """
        Begin a new transaction

        :return:
        """
        return self._retry(self.session.begin)

    def _retry(self, f: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Retry a function call in case of database errors
        """
        backoff = self._retry_backoff
        attempt = 0

        while True:
            try:
                return f(*args, **kwargs)
            except PendingRollbackError as e:
                logger.warning("Retrying operation due to PendingRollbackError: %s", e)
                self.session.rollback()
            except OperationalError as e:
                attempt += 1
                Log.event(
                    logger,
                    Log.DB_CONNECTION_FAILED,
                    "Database connection failed; retrying operation",
                    error_type=type(e).__name__,
                    retry_attempt=attempt,
                    backoff_seconds=backoff[0] if backoff else 0,
                )
            except DataError as e:
                Log.event(
                    logger,
                    Log.DB_SCHEMA_ERROR,
                    "Database schema error during operation",
                    exc_info=e,
                    **_schema_error_fields(e),
                )
                raise
            except DatabaseError:
                logger.exception("Database error during operation")
                raise
            except Exception:
                logger.exception("Unexpected error during operation")
                raise

            if len(backoff) == 0:
                logger.error("Operation failed after all retries")
                raise DatabaseError("Operation failed after all retries", None, BaseException())

            logger.info("Retrying operation in %s seconds", backoff[0])
            sleep(backoff[0] + random.uniform(0, 0.1))
            backoff = backoff[1:]
