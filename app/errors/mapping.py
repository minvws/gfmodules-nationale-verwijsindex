from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.services.exceptions import (
    BundleTooLargeError,
    ConflictError,
    CryptoServiceError,
    ForbiddenError,
    InvalidAuthHeadersError,
    InvalidKeyInfoError,
    InvalidModelError,
    InvalidResourceError,
    NotFoundError,
    PseudonymError,
    PseudonymExchangeError,
    UnauthorizedError,
)

LogAs = Literal["failure", "invalid_request"]


class ErrorSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: str
    fhir_code: str
    http_status: int
    log_as: LogAs | None = None


# `spec_for` resolves an exception through its MRO, so a subclass picks up its base
# class's spec and the order of these entries carries no meaning.
EXCEPTION_MAP: dict[type[Exception], ErrorSpec] = {
    NotFoundError: ErrorSpec(severity="error", fhir_code="not-found", http_status=404),
    ConflictError: ErrorSpec(severity="error", fhir_code="conflict", http_status=409),
    ForbiddenError: ErrorSpec(severity="error", fhir_code="forbidden", http_status=403),
    UnauthorizedError: ErrorSpec(severity="error", fhir_code="security", http_status=403),
    InvalidKeyInfoError: ErrorSpec(severity="error", fhir_code="transient", http_status=503),
    InvalidModelError: ErrorSpec(severity="error", fhir_code="structure", http_status=400, log_as="invalid_request"),
    InvalidResourceError: ErrorSpec(severity="error", fhir_code="invalid", http_status=400, log_as="invalid_request"),
    InvalidAuthHeadersError: ErrorSpec(severity="error", fhir_code="login", http_status=401),
    PseudonymError: ErrorSpec(severity="error", fhir_code="invalid", http_status=422, log_as="invalid_request"),
    PseudonymExchangeError: ErrorSpec(severity="error", fhir_code="invalid", http_status=400, log_as="failure"),
    CryptoServiceError: ErrorSpec(severity="error", fhir_code="transient", http_status=502, log_as="failure"),
    BundleTooLargeError: ErrorSpec(severity="error", fhir_code="too-costly", http_status=413, log_as="invalid_request"),
}

# Applied to any exception without a mapped type (rendered as HTTP 500). Unmapped
# failures are unexpected by definition, so they are always logged.
DEFAULT_SPEC: ErrorSpec = ErrorSpec(severity="error", fhir_code="exception", http_status=500, log_as="failure")
UNEXPECTED_ERROR_MESSAGE = "An unexpected error occurred"


def spec_for(exc: Exception) -> ErrorSpec:
    for cls in type(exc).__mro__:
        spec = EXCEPTION_MAP.get(cls)
        if spec is not None:
            return spec
    return DEFAULT_SPEC


def should_log_failure(exc: Exception) -> bool:
    return spec_for(exc).log_as == "failure"
