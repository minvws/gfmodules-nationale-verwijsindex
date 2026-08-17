import pytest
from fastapi import Request

from app.models.auth.data import AuthorizationScope
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.routers.dependencies import (
    get_auth_context,
    require_managing_request,
    require_managing_source,
    require_scope,
    require_scope_for_localization_query,
    require_source_matches_body,
    require_source_matches_query,
)
from app.services.exceptions import (
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
    UnauthorizedSourceError,
)
from tests.conftest import make_list_resource
from tests.routers.conftest import TEST_SOURCE_ID, make_auth_context


def _request_with_auth(ctx: object) -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.auth = ctx
    return request


def _params(subject: str | None = None, source: str | None = None) -> LocalizationListParams:
    return LocalizationListParams.model_construct(subject=subject, source=source)


def test_get_auth_context_returns_context_from_request_state() -> None:
    ctx = make_auth_context()
    assert get_auth_context(_request_with_auth(ctx)) is ctx


def test_require_scope_returns_context_when_scope_present() -> None:
    ctx = make_auth_context(scopes=[AuthorizationScope.CREATE])
    dependency = require_scope(AuthorizationScope.CREATE)
    assert dependency(ctx) is ctx


def test_require_scope_raises_when_scope_missing() -> None:
    ctx = make_auth_context(scopes=[AuthorizationScope.READ])
    dependency = require_scope(AuthorizationScope.CREATE)
    with pytest.raises(UnauthorizedScopeError):
        dependency(ctx)


def test_require_managing_request_returns_context_when_source_id_present() -> None:
    ctx = make_auth_context(source_id="SRC-001")
    assert require_managing_request(ctx) is ctx


def test_require_managing_request_raises_when_source_id_missing() -> None:
    ctx = make_auth_context(source_id=None)
    with pytest.raises(UnauthorizedManagingRequestError):
        require_managing_request(ctx)


def test_require_managing_source_returns_the_source_id() -> None:
    assert require_managing_source(make_auth_context(source_id="SRC-001")) == "SRC-001"


def test_require_managing_source_raises_when_source_id_missing() -> None:
    with pytest.raises(UnauthorizedManagingRequestError):
        require_managing_source(make_auth_context(source_id=None))


class TestRequireScopeForLocalizationQuery:
    """A subject without a source is a localization query and needs LOCALIZE; anything
    else is an ordinary read and needs READ."""

    def test_subject_only_requires_localize_scope(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.LOCALIZE])
        assert require_scope_for_localization_query(_params(subject="pseu"), ctx) is ctx

    def test_subject_only_raises_when_localize_scope_missing(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        with pytest.raises(UnauthorizedScopeError):
            require_scope_for_localization_query(_params(subject="pseu"), ctx)

    def test_subject_and_source_requires_only_read_scope(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        assert require_scope_for_localization_query(_params(subject="pseu", source=TEST_SOURCE_ID), ctx) is ctx

    def test_source_only_requires_only_read_scope(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        assert require_scope_for_localization_query(_params(source=TEST_SOURCE_ID), ctx) is ctx

    def test_empty_params_require_only_read_scope(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.READ])
        assert require_scope_for_localization_query(_params(), ctx) is ctx

    def test_raises_when_read_scope_missing(self) -> None:
        ctx = make_auth_context(scopes=[AuthorizationScope.LOCALIZE])
        with pytest.raises(UnauthorizedScopeError):
            require_scope_for_localization_query(_params(source=TEST_SOURCE_ID), ctx)


class TestRequireSourceMatchesBody:
    def test_returns_context_when_body_source_matches_claims(self) -> None:
        ctx = make_auth_context(source_id=TEST_SOURCE_ID)
        data = make_list_resource(source_id=TEST_SOURCE_ID)
        assert require_source_matches_body(data, ctx) is ctx

    def test_raises_when_body_source_differs_from_claims(self) -> None:
        ctx = make_auth_context(source_id=TEST_SOURCE_ID)
        data = make_list_resource(source_id="SOMEONE-ELSE")
        with pytest.raises(UnauthorizedSourceError):
            require_source_matches_body(data, ctx)

    def test_raises_when_claims_carry_no_source_id(self) -> None:
        ctx = make_auth_context(source_id=None)
        data = make_list_resource(source_id=TEST_SOURCE_ID)
        with pytest.raises(UnauthorizedSourceError):
            require_source_matches_body(data, ctx)


class TestRequireSourceMatchesQuery:
    def test_returns_context_when_query_source_matches_claims(self) -> None:
        ctx = make_auth_context(source_id=TEST_SOURCE_ID)
        assert require_source_matches_query(_params(source=TEST_SOURCE_ID), ctx) is ctx

    def test_raises_when_query_source_differs_from_claims(self) -> None:
        ctx = make_auth_context(source_id=TEST_SOURCE_ID)
        with pytest.raises(UnauthorizedSourceError):
            require_source_matches_query(_params(source="SOMEONE-ELSE"), ctx)

    def test_raises_when_claims_carry_no_source_id(self) -> None:
        ctx = make_auth_context(source_id=None)
        with pytest.raises(UnauthorizedSourceError):
            require_source_matches_query(_params(source=TEST_SOURCE_ID), ctx)

    def test_localize_query_without_source_is_unguarded(self) -> None:
        ctx = make_auth_context(source_id=None)
        params = _params(subject="pseu")
        assert params.is_localize_params() is True
        assert require_source_matches_query(params, ctx) is ctx

    def test_empty_query_is_unguarded(self) -> None:
        ctx = make_auth_context(source_id=None)
        assert require_source_matches_query(_params(), ctx) is ctx
