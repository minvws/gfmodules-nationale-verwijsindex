from app.auth import AuthContext
from app.models.auth.data import AuthorizationRole, RequestedAction


class AuthContextService:
    @staticmethod
    def validate_action(auth_headers: AuthContext, action: RequestedAction) -> bool:
        role = auth_headers.role
        match action:
            case RequestedAction.LOCALIZING:
                return AuthorizationRole.CONSULTING == role

            case RequestedAction.MANAGING:
                return AuthorizationRole.SOURCE == role
