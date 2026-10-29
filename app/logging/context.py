from collections.abc import Generator
from contextlib import contextmanager

import gfmodules.logging as gflog

from app.models.auth.context import AuthContext

ORGANIZATION = gflog.ContextField(name="organization", header=None)
URA_NUMBER = gflog.ContextField(name="ura_number", header=None)
CLAIM_FIELDS = (ORGANIZATION, URA_NUMBER)


@contextmanager
def bind_auth_claims(auth: AuthContext | None) -> Generator[None]:
    claims = (
        {}
        if auth is None
        else {ORGANIZATION.name: auth.claims.organization_name, URA_NUMBER.name: str(auth.claims.ura_number)}
    )
    with gflog.update_context(claims):
        yield
