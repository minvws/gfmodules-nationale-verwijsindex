import pytest

from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationRole, AuthorizationScope, RequestedAction
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
        role=AuthorizationRole.CONSULTING,
    )


@pytest.fixture()
def auth_context_source(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(ura_number=ura_number, oin="some-oin", source_id="some-source-id"),
        audience="some-audience",
        scope=[AuthorizationScope.READ],
        role=AuthorizationRole.SOURCE,
    )


def test_validate_action_should_return_true_when_role_consulting_and_action_localize(
    auth_context_consulting: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_consulting, RequestedAction.LOCALIZING)

    assert actual is True


def test_validate_action_sould_return_false_when_role_consulting_and_action_modifying(
    auth_context_consulting: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_consulting, RequestedAction.MANAGING)

    assert actual is False


def test_validate_should_return_true_when_role_source_and_action_modifying(
    auth_context_source: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_source, RequestedAction.MANAGING)

    assert actual is True


def test_validate_should_return_false_when_role_source_and_action_localizing(
    auth_context_source: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_source, RequestedAction.LOCALIZING)

    assert actual is False
