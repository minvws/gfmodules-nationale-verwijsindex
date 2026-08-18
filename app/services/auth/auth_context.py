from app.models.auth.context import AuthContext
from app.services.exceptions import UnauthorizedSourceError


class AuthContextService:
    @staticmethod
    def is_managing_request(context: AuthContext) -> bool:
        return context.claims.source_id is not None

    @staticmethod
    def assert_source_matches(context: AuthContext, source: str | None) -> AuthContext:
        """A client-supplied source must match the caller's authenticated source."""
        if source is not None and context.claims.source_id != source:
            raise UnauthorizedSourceError()
        return context
