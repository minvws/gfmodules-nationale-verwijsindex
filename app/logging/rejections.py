import logging

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

_DENIAL_STATUSES = frozenset({401, 403})


def summarize_reason(exc: Exception) -> str:
    if isinstance(exc, (RequestValidationError, ValidationError)):
        reasons = [
            f"{'.'.join(str(loc) for loc in err.get('loc', ()))}: {err.get('msg', '')}".strip(" :")
            for err in exc.errors()
        ]
        return "; ".join(r for r in reasons if r) or "validation error"
    return str(exc)


def log_rejection(status_code: int, exc: Exception, reason: str) -> None:
    level = logging.WARNING if status_code in _DENIAL_STATUSES else logging.INFO
    logger.log(level, "Request rejected with %s (%s): %s", status_code, type(exc).__name__, reason)
