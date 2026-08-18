import pytest

from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber
from app.services.auth.auth_context import AuthContextService
from app.services.exceptions import UnauthorizedSourceError


@pytest.fixture()
def auth_context_consulting(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=ura_number,
            organization_name="Some Organization",
            oin="some-oin",
        ),
        audience="some-audience",
        scope=[AuthorizationScope.READ],
    )


@pytest.fixture()
def auth_context_source(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(
            ura_number=ura_number,
            organization_name="Some Organization",
            oin="some-oin",
            source_id="some-source-id",
        ),
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


def test_assert_source_matches_returns_the_context_for_the_callers_own_source(
    auth_context_source: AuthContext,
) -> None:
    assert AuthContextService.assert_source_matches(auth_context_source, "some-source-id") is auth_context_source


def test_assert_source_matches_raises_for_another_source(auth_context_source: AuthContext) -> None:
    with pytest.raises(UnauthorizedSourceError):
        AuthContextService.assert_source_matches(auth_context_source, "some-other-source-id")


def test_assert_source_matches_leaves_a_request_naming_no_source_alone(
    auth_context_consulting: AuthContext,
) -> None:
    assert AuthContextService.assert_source_matches(auth_context_consulting, None) is auth_context_consulting


def test_assert_source_matches_raises_when_the_caller_has_no_source(
    auth_context_consulting: AuthContext,
) -> None:
    with pytest.raises(UnauthorizedSourceError):
        AuthContextService.assert_source_matches(auth_context_consulting, "some-source-id")
