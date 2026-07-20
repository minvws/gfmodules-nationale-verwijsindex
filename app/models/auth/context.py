from dataclasses import dataclass
from typing import List

from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber


@dataclass(frozen=True)
class AuthenticationClaims:
    ura_number: UraNumber
    organization_name: str
    source_id: str | None = None


@dataclass(frozen=True)
class AuthContext:
    """
    Authentication context extracted from the bearer token. This can be used in the route handlers
    """

    # List of claims from the token
    claims: AuthenticationClaims
    # OAuth scope
    scope: List[AuthorizationScope]
    # audience intended for
    audience: str
