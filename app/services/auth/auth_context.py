from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationRole, RequestedAction


class AuthContextService:
    @staticmethod
    def validate_action(context: AuthContext, action: RequestedAction) -> bool:
        role = context.role
        match action:
            case RequestedAction.LOCALIZING:
                return AuthorizationRole.CONSULTING == role

            case RequestedAction.MANAGING:
                return AuthorizationRole.SOURCE == role

    @staticmethod
    def is_managing_request(context: AuthContext) -> bool:
        return context.claims.source_id is not None
