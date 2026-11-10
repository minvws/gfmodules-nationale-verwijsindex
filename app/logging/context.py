import gfmodules.logging as gflog

from app.models.auth.context import AuthContext

ORGANIZATION_NAME = gflog.ContextField(name="organization_name", header=None)
ORGANIZATION_IDENTIFIER = gflog.ContextField(name="organization_identifier", header=None)
ACTING_ORGANIZATION_IDENTIFIER = gflog.ContextField(name="acting_organization_identifier", header=None)
ACTING_ORGANIZATION_NAME = gflog.ContextField(name="acting_organization_name", header=None)
CLAIM_FIELDS = (ORGANIZATION_NAME, ORGANIZATION_IDENTIFIER, ACTING_ORGANIZATION_IDENTIFIER, ACTING_ORGANIZATION_NAME)


def set_auth_claims(auth: AuthContext | None) -> None:
    claims = (
        {}
        if auth is None
        else {
            ORGANIZATION_NAME.name: auth.claims.organization_name,
            ORGANIZATION_IDENTIFIER.name: str(auth.claims.ura_number),
            ACTING_ORGANIZATION_IDENTIFIER.name: auth.claims.oin,
            ACTING_ORGANIZATION_NAME.name: auth.claims.acting_organization_name,
        }
    )
    gflog.set_context(claims)
