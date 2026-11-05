import logging

import gfmodules.logging as gflog
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.logging.events import Log

logger = logging.getLogger(__name__)

_DENIAL_STATUSES = frozenset({401, 403})
MAX_REASON_LENGTH = 500
_TRUNCATED = "..."


def _bounded(reason: str) -> str:
    if len(reason) <= MAX_REASON_LENGTH:
        return reason
    return reason[: MAX_REASON_LENGTH - len(_TRUNCATED)] + _TRUNCATED


def _describe(exc: Exception) -> str:
    if isinstance(exc, (RequestValidationError, ValidationError)):
        reasons = [
            f"{'.'.join(str(loc) for loc in err.get('loc', ()))}: {err.get('msg', '')}".strip(" :")
            for err in exc.errors()
        ]
        return "; ".join(r for r in reasons if r) or "validation error"
    return str(exc)


def summarize_reason(exc: Exception) -> str:
    return _bounded(_describe(exc))


def log_rejection(status_code: int, exc: Exception, reason: str) -> None:
    level = logging.WARNING if status_code in _DENIAL_STATUSES else logging.INFO
    logger.log(level, "Request rejected with %s (%s): %s", status_code, type(exc).__name__, reason)


def log_invalid_request(status_code: int, reason: str) -> None:
    gflog.emit(
        logger,
        Log.INVALID_REQUEST,
        "Invalid request rejected",
        fields={"http_status": status_code, "error_reason": _bounded(reason)},
    )
