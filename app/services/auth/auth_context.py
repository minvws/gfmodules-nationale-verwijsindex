from enum import Enum

from app.auth import AuthContext
from app.models.auth.headers import AuthorizationRoles


class RequestedAction(Enum):
    LOCALIZING = "localizing"
    MODIFYING = "modifying"


class AuthContextService:
    @staticmethod
    def validate_action(auth_headers: AuthContext, action: RequestedAction) -> bool:
        scope = auth_headers.scope
        match action:
            case RequestedAction.LOCALIZING:
                return AuthorizationRoles.CONSULTING.value in scope

            case RequestedAction.MODIFYING:
                return AuthorizationRoles.SOURCE.value in scope
