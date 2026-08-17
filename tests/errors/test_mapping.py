from app.errors.mapping import ErrorSpec, should_log, spec_for
from app.models.auth.data import AuthorizationScope
from app.services.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidHeaderPropertyError,
    InvalidKeyInfoError,
    InvalidModelError,
    NotFoundError,
    PseudonymError,
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
    UnauthorizedUraError,
)


def test_maps_not_found_to_404() -> None:
    assert spec_for(NotFoundError()) == ErrorSpec(severity="error", fhir_code="not-found", http_status=404)


def test_maps_conflict_to_409() -> None:
    assert spec_for(ConflictError()) == ErrorSpec(severity="error", fhir_code="conflict", http_status=409)


def test_maps_forbidden_to_403() -> None:
    assert spec_for(ForbiddenError()) == ErrorSpec(severity="error", fhir_code="forbidden", http_status=403)


def test_maps_invalid_key_info_to_503() -> None:
    assert spec_for(InvalidKeyInfoError()) == ErrorSpec(severity="error", fhir_code="transient", http_status=503)


def test_maps_invalid_model_to_structure_400() -> None:
    # InvalidModelError is a ValueError subclass but must resolve to structure/400,
    # not the generic ValueError invalid/400.
    assert spec_for(InvalidModelError("bad")) == ErrorSpec(severity="error", fhir_code="structure", http_status=400)


def test_maps_pseudonym_error_to_invalid_422() -> None:
    assert spec_for(PseudonymError()) == ErrorSpec(severity="error", fhir_code="invalid", http_status=422, log=True)


def test_maps_invalid_header_property_to_401() -> None:
    assert spec_for(InvalidHeaderPropertyError("aud", "x")) == ErrorSpec(
        severity="error", fhir_code="invalid", http_status=401
    )


def test_maps_generic_value_error_to_invalid_400() -> None:
    assert spec_for(ValueError("boom")) == ErrorSpec(severity="error", fhir_code="invalid", http_status=400, log=True)


def test_unauthorized_subclasses_resolve_via_mro_to_403() -> None:
    security_spec = ErrorSpec(severity="error", fhir_code="security", http_status=403)
    scope_err = UnauthorizedScopeError([AuthorizationScope.READ], AuthorizationScope.CREATE)
    assert spec_for(scope_err) == security_spec
    assert spec_for(UnauthorizedManagingRequestError()) == security_spec
    assert spec_for(UnauthorizedUraError()) == security_spec


def test_unmapped_exception_falls_back_to_500() -> None:
    assert spec_for(RuntimeError("unexpected")) == ErrorSpec(
        severity="error", fhir_code="expression", http_status=500, log=True
    )


def test_logging_is_a_property_of_the_spec() -> None:
    # Whether a failure is logged travels with its spec rather than in a second
    # lookup table that has to be kept in sync with EXCEPTION_MAP.
    assert spec_for(PseudonymError()).log is True
    assert spec_for(NotFoundError()).log is False


def test_should_log_pseudonym_error() -> None:
    assert should_log(PseudonymError()) is True


def test_should_log_value_error() -> None:
    assert should_log(ValueError("boom")) is True


def test_should_not_log_not_found() -> None:
    assert should_log(NotFoundError()) is False


def test_should_not_log_invalid_model_error() -> None:
    # InvalidModelError is a ValueError subclass but is explicitly mapped — not logged.
    assert should_log(InvalidModelError("bad")) is False


def test_should_log_unmapped_exception() -> None:
    assert should_log(RuntimeError("unexpected")) is True
