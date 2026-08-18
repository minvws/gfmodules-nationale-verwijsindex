from pydantic import BaseModel, ConfigDict

from app.services.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidHeaderPropertyError,
    InvalidKeyInfoError,
    InvalidModelError,
    NotFoundError,
    PseudonymError,
    UnauthorizedError,
)


class ErrorSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: str
    fhir_code: str
    http_status: int
    log: bool = False


# `spec_for` resolves an exception through its MRO, so a subclass picks up its base
# class's spec and the order of these entries carries no meaning.
EXCEPTION_MAP: dict[type[Exception], ErrorSpec] = {
    NotFoundError: ErrorSpec(severity="error", fhir_code="not-found", http_status=404),
    ConflictError: ErrorSpec(severity="error", fhir_code="conflict", http_status=409),
    ForbiddenError: ErrorSpec(severity="error", fhir_code="forbidden", http_status=403),
    UnauthorizedError: ErrorSpec(severity="error", fhir_code="security", http_status=403),
    InvalidKeyInfoError: ErrorSpec(severity="error", fhir_code="transient", http_status=503),
    InvalidModelError: ErrorSpec(severity="error", fhir_code="structure", http_status=400),
    InvalidHeaderPropertyError: ErrorSpec(severity="error", fhir_code="invalid", http_status=401),
    PseudonymError: ErrorSpec(severity="error", fhir_code="invalid", http_status=422, log=True),
    ValueError: ErrorSpec(severity="error", fhir_code="invalid", http_status=400, log=True),
}

# Applied to any exception without a mapped type (rendered as HTTP 500). Unmapped
# failures are unexpected by definition, so they are always logged.
DEFAULT_SPEC: ErrorSpec = ErrorSpec(severity="error", fhir_code="expression", http_status=500, log=True)


def spec_for(exc: Exception) -> ErrorSpec:
    for cls in type(exc).__mro__:
        spec = EXCEPTION_MAP.get(cls)
        if spec is not None:
            return spec
    return DEFAULT_SPEC


def should_log(exc: Exception) -> bool:
    return spec_for(exc).log
