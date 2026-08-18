import pytest

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


def _spec(fhir_code: str, http_status: int, *, log: bool = False) -> ErrorSpec:
    return ErrorSpec(severity="error", fhir_code=fhir_code, http_status=http_status, log=log)


def _scope_error() -> UnauthorizedScopeError:
    return UnauthorizedScopeError([AuthorizationScope.READ], AuthorizationScope.CREATE)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        pytest.param(NotFoundError(), _spec("not-found", 404), id="not-found"),
        pytest.param(ConflictError(), _spec("conflict", 409), id="conflict"),
        pytest.param(ForbiddenError(), _spec("forbidden", 403), id="forbidden"),
        pytest.param(InvalidKeyInfoError(), _spec("transient", 503), id="invalid-key-info"),
        pytest.param(InvalidHeaderPropertyError("aud", "x"), _spec("invalid", 401), id="invalid-header-property"),
        pytest.param(PseudonymError(), _spec("invalid", 422, log=True), id="pseudonym"),
        pytest.param(ValueError("boom"), _spec("invalid", 400, log=True), id="value-error"),
        pytest.param(InvalidModelError("bad"), _spec("structure", 400), id="invalid-model-outranks-value-error"),
        pytest.param(_scope_error(), _spec("security", 403), id="unauthorized-scope-via-mro"),
        pytest.param(UnauthorizedManagingRequestError(), _spec("security", 403), id="unauthorized-managing-via-mro"),
        pytest.param(UnauthorizedUraError(), _spec("security", 403), id="unauthorized-ura-via-mro"),
        pytest.param(RuntimeError("unexpected"), _spec("expression", 500, log=True), id="unmapped-falls-back-to-500"),
    ],
)
def test_spec_for_resolves_the_expected_spec(exc: Exception, expected: ErrorSpec) -> None:
    assert spec_for(exc) == expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        pytest.param(PseudonymError(), True, id="pseudonym"),
        pytest.param(ValueError("boom"), True, id="value-error"),
        pytest.param(RuntimeError("unexpected"), True, id="unmapped"),
        pytest.param(NotFoundError(), False, id="not-found"),
        pytest.param(_scope_error(), False, id="unauthorized-scope"),
        pytest.param(InvalidModelError("bad"), False, id="invalid-model-outranks-value-error"),
    ],
)
def test_should_log(exc: Exception, expected: bool) -> None:
    assert should_log(exc) is expected
