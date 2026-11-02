from collections.abc import Generator
from contextlib import contextmanager

import gfmodules.logging as gflog

from app.models.auth.context import AuthContext

ORGANIZATION_NAME = gflog.ContextField(name="organization_name", header=None)
ORGANIZATION_IDENTIFIER = gflog.ContextField(name="organization_identifier", header=None)
ACTING_ORGANIZATION_IDENTIFIER = gflog.ContextField(name="acting_organization_identifier", header=None)
ACTING_ORGANIZATION_NAME = gflog.ContextField(name="acting_organization_name", header=None)
CLAIM_FIELDS = (ORGANIZATION_NAME, ORGANIZATION_IDENTIFIER, ACTING_ORGANIZATION_IDENTIFIER, ACTING_ORGANIZATION_NAME)


@contextmanager
def bind_auth_claims(auth: AuthContext | None) -> Generator[None]:
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
    with gflog.update_context(claims):
        yield
