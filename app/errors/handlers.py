from typing import no_type_check

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.fhir import FHIRError
from app.models.fhir.resources.operation_outcome.resource import (
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)
from app.services.exceptions import (
    ConflictError,
    InvalidHeaderPropertyError,
    InvalidModelError,
    NotFoundError,
    PseudonymError,
    UnauthorizedError,
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
