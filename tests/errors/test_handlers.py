import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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
    PseudonymError,
    UnauthorizedScopeError,
    UnauthorizedSourceError,
)

_pending: dict[str, Exception] = {}


def _client() -> TestClient:
    """An app whose routes mirror the real paths the failure-event routing keys on."""
    app = FastAPI()
    register_exceptions(app)

    def boom() -> None:
        raise _pending["exc"]

    app.get("/fhir/boom")(boom)
    app.get("/rest/boom")(boom)
    app.post("/registrations")(boom)
    app.post("/fhir/List")(boom)
    app.post("/localize")(boom)
    app.get("/fhir/List")(boom)

    @app.get("/fhir/validated")
    def validated(required: int) -> None:  # noqa: ARG001 - forces a RequestValidationError
        return None

    @app.get("/rest/validated")
    def rest_validated(required: int) -> None:  # noqa: ARG001
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


class TestFailureLogging:
    """`handle_mapped_exception` logs only what the spec marks loggable, and only on
    paths that map to a failure event."""

    def test_logs_registration_failure_on_registrations_post(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().post("/registrations")

        assert Log.REFERRAL_REGISTRATION_FAILED.event_id in _event_ids(caplog)

    def test_logs_registration_failure_on_fhir_list_post(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().post("/fhir/List")

        assert Log.REFERRAL_REGISTRATION_FAILED.event_id in _event_ids(caplog)

    def test_logs_localization_failure_on_localize_post(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().post("/localize")

        assert Log.LOCALIZATION_FAILED.event_id in _event_ids(caplog)

    def test_logs_localization_failure_on_fhir_list_subject_query(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().get("/fhir/List", params={"subject:identifier": "pseu"})

        assert Log.LOCALIZATION_FAILED.event_id in _event_ids(caplog)

    def test_does_not_log_localization_for_fhir_list_query_without_subject(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().get("/fhir/List")

        assert _event_ids(caplog) == []

    def test_does_not_log_on_unrelated_path(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = PseudonymError("bad pseudonym")
        with caplog.at_level(logging.WARNING):
            _client().get("/fhir/boom")

        assert _event_ids(caplog) == []

    def test_does_not_log_expected_failures(self, caplog: pytest.LogCaptureFixture) -> None:
        # NotFoundError is mapped with log=False: an absent record is a normal outcome,
        # not something to raise an operational event about.
        _pending["exc"] = NotFoundError()
        with caplog.at_level(logging.WARNING):
            _client().post("/registrations")

        assert _event_ids(caplog) == []

    def test_logs_value_error(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = ValueError("malformed input")
        with caplog.at_level(logging.WARNING):
            _client().post("/registrations")

        assert Log.REFERRAL_REGISTRATION_FAILED.event_id in _event_ids(caplog)


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

    def test_summarizes_validation_errors_in_the_failure_log(self, caplog: pytest.LogCaptureFixture) -> None:
        # A RequestValidationError's str() is unreadable, so the handler summarizes the
        # individual field errors into "loc: msg" pairs instead.
        app = FastAPI()
        register_exceptions(app)

        @app.post("/localize")
        def localize(required: int) -> None:  # noqa: ARG001 - forces a RequestValidationError
            return None

        with caplog.at_level(logging.WARNING):
            TestClient(app, raise_server_exceptions=False).post("/localize")

        localization = [r for r in caplog.records if getattr(r, "event_id", None) == Log.LOCALIZATION_FAILED.event_id]
        assert localization, "expected a localization failure event"
        assert getattr(localization[0], "error_reason") == "query.required: Field required"


class TestUnhandledExceptionHandler:
    def test_fhir_path_hides_details_behind_operation_outcome(self, caplog: pytest.LogCaptureFixture) -> None:
        _pending["exc"] = RuntimeError("internal detail that must not leak")
        with caplog.at_level(logging.ERROR):
            resp = _client().get("/fhir/boom")

        assert resp.status_code == 500
        body = resp.json()
        assert body["issue"][0]["code"] == "expression"
        assert "internal detail" not in resp.text
        assert "RuntimeError" in resp.text

    def test_rest_path_reports_nothing_about_the_exception(self) -> None:
        _pending["exc"] = RuntimeError("internal detail that must not leak")
        resp = _client().get("/rest/boom")

        assert resp.status_code == 500
        assert resp.json() == {"error": "Internal server error"}

    def test_localize_path_logs_error_event_for_server_faults(self, caplog: pytest.LogCaptureFixture) -> None:
        # Below 500 a localization failure is a warning; at 500 it escalates.
        _pending["exc"] = RuntimeError("boom")
        with caplog.at_level(logging.WARNING):
            _client().post("/localize")

        assert Log.LOCALIZATION_ERROR.event_id in _event_ids(caplog)
        assert set(_event_ids(caplog)) == {Log.SYS_UNHANDLED_EXCEPTION.event_id, Log.LOCALIZATION_ERROR.event_id}
        assert {r.levelno for r in caplog.records if hasattr(r, "event_id")} == {logging.ERROR}

    def test_logs_the_unhandled_exception_event(self) -> None:
        request = MagicMock()
        request.url.path = "/boom"
        request.method = "GET"
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
