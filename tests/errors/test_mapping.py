import pytest

from app.errors.mapping import DEFAULT_SPEC, ErrorSpec, LogAs, should_log_failure, spec_for
from app.models.auth.data import AuthorizationScope
from app.models.fhir.resources.operation_outcome.resource import IssueType
from app.request_body_limit import RequestBodyTooLargeError
from app.services.exceptions import (
    BundleTooLargeError,
    ConflictError,
    CryptoServiceError,
    ForbiddenError,
    InvalidHeaderPropertyError,
    InvalidKeyInfoError,
    InvalidModelError,
    InvalidResourceError,
    NotFoundError,
    PseudonymError,
    PseudonymExchangeError,
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
    UnauthorizedUraError,
)


def _spec(fhir_code: IssueType, http_status: int, log_as: LogAs | None = None) -> ErrorSpec:
    return ErrorSpec(severity="error", fhir_code=fhir_code, http_status=http_status, log_as=log_as)


def _scope_error() -> UnauthorizedScopeError:
    return UnauthorizedScopeError([AuthorizationScope.READ], AuthorizationScope.CREATE)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        pytest.param(NotFoundError(), _spec("not-found", 404), id="not-found"),
        pytest.param(ConflictError(), _spec("conflict", 409), id="conflict"),
        pytest.param(ForbiddenError(), _spec("forbidden", 403), id="forbidden"),
        pytest.param(InvalidKeyInfoError(), _spec("transient", 503), id="invalid-key-info"),
        pytest.param(InvalidHeaderPropertyError("aud", "x"), _spec("login", 401), id="invalid-header-property"),
        pytest.param(PseudonymError(), _spec("invalid", 422, "invalid_request"), id="pseudonym"),
        pytest.param(InvalidResourceError("bad"), _spec("invalid", 400, "invalid_request"), id="invalid-resource"),
        pytest.param(ValueError("boom"), DEFAULT_SPEC, id="value-error-is-unexpected"),
        pytest.param(PseudonymExchangeError("rejected"), _spec("invalid", 400, "failure"), id="pseudonym-exchange"),
        pytest.param(CryptoServiceError("down"), _spec("transient", 502, "failure"), id="crypto-service"),
        pytest.param(
            BundleTooLargeError("too many"), _spec("too-costly", 413, "invalid_request"), id="bundle-too-large"
        ),
        pytest.param(
            RequestBodyTooLargeError(10), _spec("too-long", 413, "invalid_request"), id="request-body-too-large"
        ),
        pytest.param(InvalidModelError("bad"), _spec("structure", 400, "invalid_request"), id="invalid-model"),
        pytest.param(_scope_error(), _spec("security", 403), id="unauthorized-scope-via-mro"),
        pytest.param(UnauthorizedManagingRequestError(), _spec("security", 403), id="unauthorized-managing-via-mro"),
        pytest.param(UnauthorizedUraError(), _spec("security", 403), id="unauthorized-ura-via-mro"),
        pytest.param(RuntimeError("unexpected"), _spec("exception", 500, "failure"), id="unmapped-falls-back-to-500"),
    ],
)
def test_spec_for_resolves_the_expected_spec(exc: Exception, expected: ErrorSpec) -> None:
    assert spec_for(exc) == expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        pytest.param(PseudonymError(), False, id="pseudonym"),
        pytest.param(ValueError("boom"), True, id="value-error"),
        pytest.param(PseudonymExchangeError("rejected"), True, id="pseudonym-exchange"),
        pytest.param(RuntimeError("unexpected"), True, id="unmapped"),
        pytest.param(NotFoundError(), False, id="not-found"),
        pytest.param(_scope_error(), False, id="unauthorized-scope"),
        pytest.param(InvalidModelError("bad"), False, id="invalid-model-outranks-value-error"),
    ],
)
def test_should_log_failure(exc: Exception, expected: bool) -> None:
    assert should_log_failure(exc) is expected
