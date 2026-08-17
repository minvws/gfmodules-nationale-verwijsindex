from typing import Annotated, Callable

from fastapi import Body, Depends, Query, Request

from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.services.auth.auth_context import AuthContextService
from app.services.exceptions import (
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
    UnauthorizedSourceError,
)


def get_auth_context(request: Request) -> AuthContext:
    ctx: AuthContext = request.state.auth
    return ctx


def require_scope(scope: AuthorizationScope) -> Callable[..., AuthContext]:
    def dependency(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if scope not in ctx.scope:
            raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=scope)
        return ctx

    return dependency


def require_managing_request(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not AuthContextService.is_managing_request(ctx):
        raise UnauthorizedManagingRequestError()
    return ctx


def require_managing_source(ctx: AuthContext = Depends(get_auth_context)) -> str:
    """The source the caller is authenticated as, for operations that must have one.

    Same guard as :func:`require_managing_request`, but returns the source itself so a
    route that stores it receives a ``str`` rather than re-narrowing an optional claim.
    """
    source_id = require_managing_request(ctx).claims.source_id
    assert source_id is not None  # noqa: S101 - guaranteed by require_managing_request
    return source_id


def require_scope_for_localization_query(
    params: Annotated[LocalizationListParams, Query()],
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """Require LOCALIZE scope for localization queries, READ scope for other queries."""
    required_scope = AuthorizationScope.LOCALIZE if params.is_localize_params() else AuthorizationScope.READ
    if required_scope not in ctx.scope:
        raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=required_scope)
    return ctx


def _assert_source_matches(ctx: AuthContext, source: str | None) -> AuthContext:
    """A client-supplied source must match the caller's authenticated source.

    A request that supplies no source is left unguarded: localization queries carry a
    subject and no source, so they pass through without needing a special case.
    """
    if source is not None and ctx.claims.source_id != source:
        raise UnauthorizedSourceError()
    return ctx


def require_source_matches_body(
    # NOTE: this parameter's name and type must stay identical to the body parameter of
    # the route that depends on it. FastAPI merges body parameters across the dependency
    # tree by name, so renaming either side turns one body into two embedded fields and
    # every request fails with 422 - a runtime break that mypy cannot see.
    data: Annotated[LocalizationList, Body(media_type="application/fhir+json")],
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    return _assert_source_matches(ctx, data.get_device())


def require_source_matches_query(
    params: Annotated[LocalizationListParams, Query()],
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    return _assert_source_matches(ctx, params.source)
