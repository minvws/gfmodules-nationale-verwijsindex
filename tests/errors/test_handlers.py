import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging.middleware import RequestContext
from gfmodules.logging.testing import assert_event_emitted, capture_records

from app.errors import handlers
from app.errors.handlers import handle_unhandled_exception, register_exceptions
from app.logging.events import Log
from app.models.auth.data import AuthorizationScope
from app.services.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidKeyInfoError,
    InvalidModelError,
    NotFoundError,
    UnauthorizedScopeError,
    UnauthorizedSourceError,
)

_pending: dict[str, Exception] = {}


def _client() -> TestClient:
    app = FastAPI()
    register_exceptions(app)

    def boom() -> None:
        raise _pending["exc"]

    app.get("/fhir/boom")(boom)
    app.get("/rest/boom")(boom)
    app.get("/fhir/List")(boom)

    @app.get("/fhir/validated")
    def validated(required: int) -> None:
        return None

    @app.get("/rest/validated")
    def rest_validated(required: int) -> None:
        return None

    return TestClient(app, raise_server_exceptions=False)


def _event_ids(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.event_id for r in caplog.records if hasattr(r, "event_id")]


@pytest.mark.parametrize(
    "exc, status, code",
    [
        (InvalidModelError("bad bundle"), 400, "structure"),
        (NotFoundError(), 404, "not-found"),
        (ConflictError(), 409, "conflict"),
        (UnauthorizedScopeError([AuthorizationScope.READ], AuthorizationScope.CREATE), 403, "security"),
        (ForbiddenError(), 403, "forbidden"),
        (InvalidKeyInfoError(), 503, "transient"),
    ],
)
def test_fhir_path_renders_operation_outcome(exc: Exception, status: int, code: str) -> None:
    _pending["exc"] = exc
    resp = _client().get("/fhir/boom")
    assert resp.status_code == status
    body = resp.json()
    assert body["issue"][0]["code"] == code
    assert resp.headers["Content-type"] == "application/fhir+json"


def test_rest_path_renders_plain_string() -> None:
    _pending["exc"] = NotFoundError()
    resp = _client().get("/rest/boom")
    assert resp.status_code == 404
    assert resp.json() == "Record not found"


class TestRejectionLogging:
    def test_authorisation_denial_is_logged_as_a_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = UnauthorizedSourceError()
        with caplog.at_level(logging.WARNING):
            resp = _client().get("/fhir/boom")

        assert resp.status_code == 403
        assert "The requested source does not match the authenticated source" in caplog.text
        assert "UnauthorizedSourceError" in caplog.text

    def test_denial_is_logged_on_routes_without_a_failure_event(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = UnauthorizedSourceError()
        with caplog.at_level(logging.WARNING):
            _client().get("/fhir/List")

        assert _event_ids(caplog) == []
        assert "The requested source does not match the authenticated source" in caplog.text

    def test_routine_failures_stay_below_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = NotFoundError()
        with caplog.at_level(logging.WARNING):
            _client().get("/fhir/boom")

        assert caplog.records == []

    def test_routine_failures_are_still_logged_at_info(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = NotFoundError()
        with caplog.at_level(logging.INFO):
            _client().get("/fhir/boom")

        assert "Record not found" in caplog.text


class TestRequestValidationHandler:
    def test_fhir_path_renders_operation_outcome_issues(self) -> None:
        resp = _client().get("/fhir/validated")

        assert resp.status_code == 422
        body = resp.json()
        assert body["issue"][0]["code"] == "required"
        assert "required" in body["issue"][0]["details"]["text"]
        assert resp.headers["Content-Type"] == "application/fhir+json"

    def test_rest_path_renders_error_list(self) -> None:
        resp = _client().get("/rest/validated")

        assert resp.status_code == 422
        assert isinstance(resp.json(), list)

    def test_marks_non_missing_errors_as_invalid(self) -> None:
        resp = _client().get("/fhir/validated", params={"required": "not-an-int"})

        assert resp.status_code == 422
        assert resp.json()["issue"][0]["code"] == "invalid"

    def test_summarizes_validation_errors_in_the_rejection_log(self, caplog: pytest.LogCaptureFixture) -> None:
        # A RequestValidationError's str() is unreadable, so the handler summarizes the
        # individual field errors into "loc: msg" pairs instead.
        with caplog.at_level(logging.INFO):
            _client().get("/rest/validated")

        assert "query.required: Field required" in caplog.text


class TestUnhandledExceptionHandler:
    def test_fhir_path_hides_details_behind_operation_outcome(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = RuntimeError("internal detail that must not leak")
        with caplog.at_level(logging.ERROR):
            resp = _client().get("/fhir/boom")

        assert resp.status_code == 500
        body = resp.json()
        assert body["issue"][0]["code"] == "exception"
        assert "internal detail" not in resp.text
        assert "RuntimeError" in resp.text

    def test_rest_path_reports_nothing_about_the_exception(self) -> None:
        _pending["exc"] = RuntimeError("internal detail that must not leak")
        resp = _client().get("/rest/boom")

        assert resp.status_code == 500
        assert resp.json() == {"error": "Internal server error"}

    def test_logs_the_unhandled_exception_event(self) -> None:
        request = MagicMock()
        request.url.path = "/boom"
        request.method = "GET"
        request.state.request_context = RequestContext(values={"endpoint": "/boom", "method": "GET"})
        exc = RuntimeError("explode")

        with capture_records(handlers.logger.name) as records:
            response = handle_unhandled_exception(request, exc)

        assert response.status_code == 500
        assert json.loads(response.body) == {"error": "Internal server error"}  # type: ignore
        entry = assert_event_emitted(
            records,
            Log.SYS_UNHANDLED_EXCEPTION,
            exception_type="RuntimeError",
            endpoint="/boom",
            method="GET",
        )
        assert entry.record.exc_info is not None
