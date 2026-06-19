from app.models.auth.context import AuthContext


class AuthContextService:
    @staticmethod
    def is_managing_request(context: AuthContext) -> bool:
        return context.claims.source_id is not None
