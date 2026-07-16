import logging
from typing import no_type_check

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.fhir import FHIRError
from app.logging.events import Log, NVIEvent
from app.models.fhir.resources.localization_list.request import SUBJECT_IDENTIFIER_PARAM
from app.models.fhir.resources.operation_outcome.resource import (
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)
from app.services.exceptions import (
    ConflictError,
    ForbiddedError,
    InvalidHeaderPropertyError,
    InvalidKeyInfoError,
    InvalidModelError,
    NotFoundError,
    PseudonymError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)


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


def handle_not_found_error(request: Request, exception: NotFoundError) -> JSONResponse:
    path = request.url.path
    status_code = 404
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="not-found", msg=str(exception))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(
        content=str(exception),
        status_code=status_code,
    )


def handle_conflict_error(request: Request, exception: ConflictError) -> JSONResponse:
    path = request.url.path
    status_code = 409
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="conflict", msg=str(exception))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exception))


def handle_unauthorized_error(req: Request, exc: UnauthorizedError) -> JSONResponse:
    path = req.url.path
    status_code = 403
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="security", msg=str(exc))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exc))


def handle_forbidden_error(req: Request, exc: ForbiddedError) -> JSONResponse:
    path = req.url.path
    status_code = 403
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="forbidden", msg=str(exc))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exc))


def handle_invalid_key_info_error(req: Request, exc: InvalidKeyInfoError) -> JSONResponse:
    path = req.url.path
    status_code = 503
    fhir_error = FHIRError(severity="error", code="transient", msg=str(exc))
    if "fhir" in path:
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
        )

    return JSONResponse(status_code=status_code, content=str(exc))


def hanlde_invalid_model_errors(request: Request, exception: InvalidModelError) -> Response:
    path = request.url.path
    status_code = 400
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="structure", msg=str(exception))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exception))


def handle_pseudonym_decoding_error(request: Request, exception: PseudonymError) -> Response:
    path = request.url.path
    status_code = 400
    log_request_failure(request, status_code, exception)
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="invalid", msg=str(exception))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exception))


def handle_value_error(request: Request, exception: ValueError) -> JSONResponse:
    path = request.url.path
    status_code = 400
    log_request_failure(request, status_code, exception)
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="invalid", msg=str(exception))
        return JSONResponse(
            status_code=status_code,
            content=fhir_error.outcome.model_dump(exclude_none=True),
            headers=fhir_error.headers,
        )

    return JSONResponse(status_code=status_code, content=str(exception))


def handle_invalid_header_property_error(req: Request, exc: InvalidHeaderPropertyError) -> JSONResponse:
    path = req.url.path
    status_code = 401
    if "fhir" in path:
        fhir_error = FHIRError(severity="error", code="invalid", msg=str(exc))
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


def default_exception_handler(req: Request, exc: Exception) -> JSONResponse:
    path = req.url.path
    status_code = 500
    log_request_failure(req, status_code, exc)
    if "fhir" in path:
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

    return JSONResponse(
        status_code=status_code,
        content=f"An unexpected error occurred {type(exc).__name__}",
    )


@no_type_check
def register_exceptions(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, handle_not_found_error)
    app.add_exception_handler(UnauthorizedError, handle_unauthorized_error)
    app.add_exception_handler(PseudonymError, handle_pseudonym_decoding_error)
    app.add_exception_handler(ConflictError, handle_conflict_error)
    app.add_exception_handler(InvalidHeaderPropertyError, handle_invalid_header_property_error)

    app.add_exception_handler(RequestValidationError, handle_request_validation_exception)
    app.add_exception_handler(ValueError, handle_value_error)
    app.add_exception_handler(Exception, default_exception_handler)
