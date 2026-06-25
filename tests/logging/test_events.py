import logging

import pytest

from app.logging.events import Log
from app.logging.filters import LoggingStreams


def test_log_event_attaches_event_id_and_streams(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events"):
        Log.event(logger, Log.SYS_APP_STARTED, "started", version="1.0")

    record = caplog.records[-1]
    assert record.event_id == Log.SYS_APP_STARTED.event_id  # type: ignore
    assert LoggingStreams.APP in record.stream  # type: ignore
    assert record.version == "1.0"  # type: ignore
    assert record.levelno == logging.INFO


@pytest.mark.parametrize(
    "event,expected_level",
    [
        (Log.SYS_APP_STARTED, logging.INFO),
        (Log.HEALTH_UNHEALTHY, logging.ERROR),
        (Log.SYS_UNHANDLED_EXCEPTION, logging.ERROR),
    ],
)
def test_log_event_uses_event_level(caplog: pytest.LogCaptureFixture, event: object, expected_level: int) -> None:
    logger = logging.getLogger("app.test_events_levels")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_levels"):
        Log.event(logger, event, "msg")  # type: ignore[arg-type]
    assert caplog.records[-1].levelno == expected_level


def test_log_event_attaches_field_streams_for_routed_events(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events_routing")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_routing"):
        Log.event(logger, Log.REGISTERED_REFERRAL, "registered", ura_number="12345678")

    record = caplog.records[-1]
    field_streams = record.field_streams  # type: ignore[attr-defined]
    assert field_streams[LoggingStreams.PUBLIC_INSPECT] == ("organization", "ura_number", "pseudonym_hash")
    assert field_streams[LoggingStreams.APP] == ("ura_number",)
    assert LoggingStreams.SIEM not in field_streams


def test_log_event_omits_field_streams_for_plain_events(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events_plain")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="app.test_events_plain"):
        Log.event(logger, Log.SYS_APP_STARTED, "started")

    assert not hasattr(caplog.records[-1], "field_streams")


def test_log_event_includes_exc_info(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("app.test_events_exc")
    logger.setLevel(logging.DEBUG)
    try:
        raise ValueError("boom")
    except ValueError as e:
        with caplog.at_level(logging.DEBUG, logger="app.test_events_exc"):
            Log.event(logger, Log.SYS_UNHANDLED_EXCEPTION, "fail", exc_info=e)

    assert caplog.records[-1].exc_info is not None
