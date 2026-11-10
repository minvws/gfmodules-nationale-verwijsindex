import gfmodules.logging as gflog

from app.models.auth.context import AuthContext

REPRESENTED_ORGANIZATION_NAME = gflog.ContextField(name="represented_organization_name", header=None)
REPRESENTED_ORGANIZATION_IDENTIFIER = gflog.ContextField(name="represented_organization_identifier", header=None)
ACTING_ORGANIZATION_IDENTIFIER = gflog.ContextField(name="acting_organization_identifier", header=None)
ACTING_ORGANIZATION_NAME = gflog.ContextField(name="acting_organization_name", header=None)
CLAIM_FIELDS = (
    REPRESENTED_ORGANIZATION_NAME,
    REPRESENTED_ORGANIZATION_IDENTIFIER,
    ACTING_ORGANIZATION_IDENTIFIER,
    ACTING_ORGANIZATION_NAME,
)


def set_auth_claims(auth: AuthContext | None) -> None:
    claims = (
        {}
        if auth is None
        else {
            REPRESENTED_ORGANIZATION_NAME.name: auth.claims.organization_name,
            REPRESENTED_ORGANIZATION_IDENTIFIER.name: str(auth.claims.ura_number),
            ACTING_ORGANIZATION_IDENTIFIER.name: auth.claims.oin,
            ACTING_ORGANIZATION_NAME.name: auth.claims.acting_organization_name,
        }
    )
    gflog.set_context(claims)
