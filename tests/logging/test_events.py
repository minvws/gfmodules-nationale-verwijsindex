import logging

import gfmodules.logging as gflog
import pytest
from gfmodules.logging import DefaultEventCatalogue, LoggingStreams
from gfmodules.logging.events import declared_events
from gfmodules.logging.testing import assert_catalogue_complete, assert_event_emitted, capture_records

from app.logging.events import Log

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM
_PUB = LoggingStreams.PUBLIC_INSPECT


class TestCatalogue:
    def test_defines_every_required_event(self) -> None:
        assert_catalogue_complete(Log)

    @pytest.mark.parametrize(
        "name,event_id",
        [
            ("HEALTH_UNHEALTHY", "100600"),
            ("SYS_APP_STARTED", "100601"),
            ("SYS_APP_STOPPED", "100602"),
            ("SYS_APP_CRASHED", "100602"),
            ("DB_CONNECTION_FAILED", "100603"),
            ("SYS_UNHANDLED_EXCEPTION", "100604"),
            ("DB_SCHEMA_ERROR", "100605"),
            ("SYS_MISSING_CORRELATION_ID", "100606"),
            ("ACCESS_REQUEST", "094500"),
            ("REGISTERED_REFERRAL", "900400"),
            ("IDEMPOTENT_REGISTRATION", "900401"),
            ("REFERRAL_SEARCHED_ON_ID", "900402"),
            ("REFERRALS_QUERIED", "900403"),
            ("REFERRAL_REGISTRATION_FAILED", "900404"),
            ("REFERRAL_ACCESS_DENIED", "900405"),
            ("REFERRAL_DELETED", "900500"),
            ("ALL_PATIENT_REFERRALS_DELETED", "900501"),
            ("ALL_URA_REFERRALS_DELETED", "900503"),
            ("LOCALIZATION_SUCCESS", "900600"),
            ("LOCALIZATION_FAILED", "900601"),
            ("LOCALIZATION_ERROR", "900601"),
            ("LOCALIZATION_NO_MATCH", "900602"),
        ],
    )
    def test_carries_the_event_id_the_spec_assigns(self, name: str, event_id: str) -> None:
        assert getattr(Log, name).event_id == event_id

    def test_every_declared_event_routes_at_least_one_stream(self) -> None:
        for name, event in declared_events(Log):
            assert event.streams, f"{name} declares no stream"

    def test_every_allow_list_names_a_stream_the_event_routes(self) -> None:
        for name, event in declared_events(Log):
            unrouted = set(event.fields) - set(event.streams)
            assert not unrouted, f"{name} allow-lists fields for streams it does not route: {unrouted}"


class TestOverriddenSystemEvents:
    def test_app_started_reports_whether_the_crypto_service_api_is_enabled(self) -> None:
        assert "crypto_service_api_enabled" in Log.SYS_APP_STARTED.fields[_APP]
        assert "crypto_service_api_enabled" not in DefaultEventCatalogue.SYS_APP_STARTED.fields[_APP]


class TestInheritedSystemEvents:
    @pytest.mark.parametrize(
        "name",
        [
            "SYS_APP_STOPPED",
            "SYS_APP_CRASHED",
            "SYS_UNHANDLED_EXCEPTION",
            "SYS_MISSING_CORRELATION_ID",
            "ACCESS_REQUEST",
        ],
    )
    def test_keeps_the_shared_routing(self, name: str) -> None:
        event = getattr(Log, name)
        default = getattr(DefaultEventCatalogue, name)

        assert (event.level, event.streams, event.fields) == (default.level, default.streams, default.fields)

    def test_access_request_carries_the_status_and_duration_the_middleware_emits(self) -> None:
        assert "status_code" in Log.ACCESS_REQUEST.fields[_APP]
        assert "duration_ms" in Log.ACCESS_REQUEST.fields[_APP]


class TestEmitting:
    def test_stamps_the_event_id_level_and_fields_on_the_record(self) -> None:
        logger = logging.getLogger("app.test_events")
        with capture_records("app.test_events") as records:
            gflog.emit(logger, Log.REGISTERED_REFERRAL, "registered", fields={"ura_number": "12345678"})

        entry = assert_event_emitted(records, Log.REGISTERED_REFERRAL, ura_number="12345678")
        assert entry.level == "INFO"
        assert entry.description == "registered"

    def test_carries_the_exception_when_one_is_passed(self) -> None:
        logger = logging.getLogger("app.test_events")
        try:
            raise ValueError("boom")
        except ValueError as exc:
            with capture_records("app.test_events") as records:
                gflog.emit(
                    logger, Log.SYS_UNHANDLED_EXCEPTION, "failed", fields={"exception_type": "ValueError"}, exc_info=exc
                )

        assert records.entries[-1].record.exc_info is not None
