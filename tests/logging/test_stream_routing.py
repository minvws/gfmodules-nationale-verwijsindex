import logging
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any

import gfmodules.logging as gflog
import pytest
from gfmodules.logging import LogEvent, LoggingStreams, bind_context
from gfmodules.logging.testing import assert_fields_absent, capture_stream

from app.logging.events import Log

_LOGGER_NAME = "app.test_stream_routing"
_ORGANIZATION = "some_name"
_URA = "12345678"
_PSEUDONYM_HASH = "abcd1234abcd1234"

Routed = dict[LoggingStreams, list[dict[str, Any]]]


@pytest.fixture
def route() -> Iterator[Any]:
    logger = logging.getLogger(_LOGGER_NAME)

    def _route(event: LogEvent, message: str = "event", **fields: Any) -> Routed:
        with ExitStack() as stack:
            routed: Routed = {
                stream: stack.enter_context(capture_stream(stream, _LOGGER_NAME)) for stream in LoggingStreams
            }
            gflog.emit(logger, event, message, fields={**fields})
        return routed

    with bind_context(
        {
            "request_id": "req-1",
            "ip": "10.0.0.1",
            "endpoint": "/token",
            "method": "POST",
            "correlation_id": "corr-1",
        }
    ):
        yield _route


class TestReferralRegistration:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(
                Log.REGISTERED_REFERRAL,
                "registered",
                organization=_ORGANIZATION,
                ura_number=_URA,
                pseudonym_hash=_PSEUDONYM_HASH,
            )
        )

    def test_public_inspect_receives_the_organization_and_pseudonym_hash(self, routed: Routed) -> None:
        message = routed[LoggingStreams.PUBLIC_INSPECT][0]
        assert message["organization"] == _ORGANIZATION
        assert message["ura_number"] == _URA
        assert message["pseudonym_hash"] == _PSEUDONYM_HASH

    def test_app_receives_the_ura_number_but_not_the_pseudonym_hash(self, routed: Routed) -> None:
        assert routed[LoggingStreams.APP][0]["ura_number"] == _URA
        assert_fields_absent(routed[LoggingStreams.APP], "pseudonym_hash", "organization")

    def test_siem_receives_nothing_at_all(self, routed: Routed) -> None:
        assert routed[LoggingStreams.SIEM] == []

    def test_correlation_metadata_is_retained_in_every_routed_stream(self, routed: Routed) -> None:
        for stream in (LoggingStreams.PUBLIC_INSPECT, LoggingStreams.APP):
            message = routed[stream][0]
            assert message["request_id"] == "req-1"
            assert message["ip"] == "10.0.0.1"
            assert message["correlation_id"] == "corr-1"


class TestReferralAccessDenied:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(Log.REFERRAL_ACCESS_DENIED, "access denied", ura_number=_URA, resource_ura="87654321"),
        )

    def test_app_receives_the_endpoint_and_siem_does_not(self, routed: Routed) -> None:
        assert routed[LoggingStreams.APP][0]["endpoint"] == "/token"
        assert routed[LoggingStreams.SIEM][0]["resource_ura"] == "87654321"
        assert_fields_absent(routed[LoggingStreams.SIEM], "endpoint")

    def test_public_inspect_receives_nothing(self, routed: Routed) -> None:
        assert routed[LoggingStreams.PUBLIC_INSPECT] == []


class TestLocalization:
    @pytest.fixture
    def routed(self, route: Any) -> Routed:
        return dict(
            route(
                Log.LOCALIZATION_SUCCESS,
                "localized",
                organization=_ORGANIZATION,
                ura_number=_URA,
                pseudonym_hash=_PSEUDONYM_HASH,
                result_count=3,
            )
        )

    def test_public_inspect_receives_the_organization_but_not_the_result_count(self, routed: Routed) -> None:
        message = routed[LoggingStreams.PUBLIC_INSPECT][0]
        assert message["organization"] == _ORGANIZATION
        assert message["pseudonym_hash"] == _PSEUDONYM_HASH
        assert_fields_absent(routed[LoggingStreams.PUBLIC_INSPECT], "result_count")

    def test_app_receives_the_pseudonym_hash_but_not_the_organization(self, routed: Routed) -> None:
        message = routed[LoggingStreams.APP][0]
        assert message["ura_number"] == _URA
        assert message["pseudonym_hash"] == _PSEUDONYM_HASH
        assert_fields_absent(routed[LoggingStreams.APP], "result_count", "organization")

    def test_the_pseudonym_hash_never_reaches_siem(self, routed: Routed) -> None:
        message = routed[LoggingStreams.SIEM][0]
        assert message["ura_number"] == _URA
        assert message["result_count"] == 3
        assert_fields_absent(routed[LoggingStreams.SIEM], "pseudonym_hash", "organization")


class TestBulkDeletion:
    def test_all_ura_referrals_deleted_reaches_all_three_streams(self, route: Any) -> None:
        routed: Routed = route(
            Log.ALL_URA_REFERRALS_DELETED,
            "all referrals deleted",
            organization=_ORGANIZATION,
            ura_number=_URA,
            deleted_count=42,
        )

        for stream in LoggingStreams:
            assert routed[stream][0]["deleted_count"] == 42
        assert_fields_absent(routed[LoggingStreams.APP], "organization")
        assert_fields_absent(routed[LoggingStreams.SIEM], "organization")


class TestAccessRequest:
    def test_reaches_the_app_stream_only(self, route: Any) -> None:
        routed: Routed = route(Log.ACCESS_REQUEST, "access", status_code=200, duration_ms=5)

        message = routed[LoggingStreams.APP][0]
        assert message["endpoint"] == "/token"
        assert message["method"] == "POST"
        assert message["status_code"] == 200
        assert message["duration_ms"] == 5

        assert routed[LoggingStreams.PUBLIC_INSPECT] == []
        assert routed[LoggingStreams.SIEM] == []
