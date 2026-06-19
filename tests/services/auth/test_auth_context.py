import pytest

from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber
from app.services.auth.auth_context import AuthContextService


@pytest.fixture()
def auth_context_consulting(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=ura_number,
            oin="some-oin",
        ),
        audience="some-audience",
        scope=[AuthorizationScope.READ],
    )


@pytest.fixture()
def auth_context_source(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(ura_number=ura_number, oin="some-oin", source_id="some-source-id"),
        audience="some-audience",
        scope=[AuthorizationScope.READ],
    )


def test_is_managing_request_should_return_true_when_source_exists(
    auth_context_source: AuthContext,
) -> None:
    actual = AuthContextService.is_managing_request(auth_context_source)

    assert actual is True


def test_is_managing_request_should_return_fals_when_source_is_missing(
    auth_context_consulting: AuthContext,
) -> None:
    actual = AuthContextService.is_managing_request(auth_context_consulting)

    assert actual is False
