import pytest

from app.auth import AuthContext
from app.models.auth.headers import AuthorizationRoles
from app.models.ura import UraNumber
from app.services.auth.auth_context import AuthContextService, RequestedAction


@pytest.fixture()
def auth_context_consulting(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims={},
        scope=["nvi:read"],
        ura_number=ura_number,
        oin="some-oin",
        role=AuthorizationRoles.CONSULTING.value,
    )


@pytest.fixture()
def auth_context_source(ura_number: UraNumber) -> AuthContext:
    return AuthContext(
        claims={},
        scope=["nvi:read"],
        ura_number=ura_number,
        oin="some-oin",
        role=AuthorizationRoles.SOURCE.value,
    )


def test_validate_action_should_return_true_when_role_consulting_and_action_localize(
    auth_context_consulting: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_consulting, RequestedAction.LOCALIZING)

    assert actual is True


def test_validate_action_sould_return_false_when_role_consulting_and_action_modifying(
    auth_context_consulting: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_consulting, RequestedAction.MODIFYING)

    assert actual is False


def test_validate_should_return_true_when_role_source_and_action_modifying(
    auth_context_source: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_source, RequestedAction.MODIFYING)

    assert actual is True


def test_validate_should_return_false_when_role_source_and_action_localizing(
    auth_context_source: AuthContext,
) -> None:
    actual = AuthContextService.validate_action(auth_context_source, RequestedAction.LOCALIZING)

    assert actual is False
