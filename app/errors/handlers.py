import logging
from typing import no_type_check

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.fhir import FHIRError
from app.errors.mapping import EXCEPTION_MAP, should_log, spec_for
from app.logging.events import Log, NVIEvent
from app.logging.middleware import restore_request_context
from app.models.fhir.resources.localization_list.request import SUBJECT_IDENTIFIER_PARAM
from app.models.fhir.resources.operation_outcome.resource import (
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)

logger = logging.getLogger(__name__)

_DENIAL_STATUSES = frozenset({401, 403})


def _failure_event_for(request: Request, status_code: int) -> NVIEvent | None:
    path = request.url.path
    method = request.method
    if method == "POST" and (path.endswith("/registrations") or path.endswith("/fhir/List")):
        return Log.REFERRAL_REGISTRATION_FAILED
    localize_failed_rest = method == "POST" and path.endswith("/localize")
    localize_failed_fhir = (
        method == "GET" and path.endswith("/fhir/List") and request.query_params.get(SUBJECT_IDENTIFIER_PARAM)
    )
    if localize_failed_rest or localize_failed_fhir:
        if status_code < 500:
            return Log.LOCALIZATION_FAILED
        else:
            return Log.LOCALIZATION_ERROR
    return None


def _summarize_reason(exc: Exception) -> str:
    if isinstance(exc, RequestValidationError):
        reasons = [
            f"{'.'.join(str(loc) for loc in err.get('loc', ()))}: {err.get('msg', '')}".strip(" :")
            for err in exc.errors()
        ]
        return "; ".join(r for r in reasons if r) or "validation error"
    return str(exc)


def log_request_failure(request: Request, status_code: int, exc: Exception) -> None:
    event = _failure_event_for(request, status_code)
    if event is None:
        return
    auth = getattr(request.state, "auth", None)
    Log.event(
        logger,
        event,
        ("Referral registration failed" if event is Log.REFERRAL_REGISTRATION_FAILED else "Localization failed"),
        ura_number=str(auth.claims.ura_number) if auth is not None else None,
        http_status=status_code,
        error_reason=_summarize_reason(exc),
    )


def _log_rejection(request: Request, status_code: int, exc: Exception) -> None:
    """Record why a request was rejected."""
    level = logging.WARNING if status_code in _DENIAL_STATUSES else logging.INFO
    logger.log(
        level,
        "Request rejected with %s (%s): %s",
        status_code,
        type(exc).__name__,
        _summarize_reason(exc),
    )


def handle_mapped_exception(request: Request, exc: Exception) -> JSONResponse:
    spec = spec_for(exc)
    status_code = spec.http_status
    _log_rejection(request, status_code, exc)
    if should_log(exc):
        log_request_failure(request, status_code, exc)

    if "fhir" in request.url.path:
        fhir_error = FHIRError(severity=spec.severity, code=spec.fhir_code, msg=str(exc))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exc))


def handle_request_validation_exception(req: Request, exc: RequestValidationError) -> JSONResponse:
    path = req.url.path
    status_code = 422
    log_request_failure(req, status_code, exc)
    if "fhir" in path:
        issues = []

        for err in exc.errors():
            issues.append(
                OperationOutcomeIssue(
                    severity="error",
                    code="required" if err["type"] == "missing" else "invalid",
                    details=OperationOutcomeDetail(text=".".join(map(str, err["loc"])) + " " + str(err["msg"])),
                ),
            )

        outcome = OperationOutcome(issue=issues)

        return JSONResponse(
            status_code=status_code,
            content=outcome.model_dump(by_alias=True, exclude_none=True),
            headers={"Content-Type": "application/fhir+json"},
        )

    return JSONResponse(status_code=status_code, content=exc.errors())


@restore_request_context
def handle_unhandled_exception(req: Request, exc: Exception) -> JSONResponse:
    status_code = 500
    Log.event(
        logger,
        Log.SYS_UNHANDLED_EXCEPTION,
        "Unhandled exception",
        exc_info=exc,
        exception_type=type(exc).__name__,
        endpoint=req.url.path,
        method=req.method,
    )
    log_request_failure(req, status_code, exc)
    if "fhir" in req.url.path:
        fhir_error = FHIRError(
            severity="error",
            code="expression",
            msg="An unexpected error occurred",
            expression=[type(exc).__name__],
        )

        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content={"error": "Internal server error"})


@no_type_check
def register_exceptions(app: FastAPI) -> None:
    for exception_type in EXCEPTION_MAP:
        app.add_exception_handler(exception_type, handle_mapped_exception)

    app.add_exception_handler(RequestValidationError, handle_request_validation_exception)
    app.add_exception_handler(Exception, handle_unhandled_exception)
