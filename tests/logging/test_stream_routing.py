"""Integration tests for per-field stream routing.

Wires up the APP (stroom 2) and SIEM (stroom 3) handlers the same way
``LogConfigBuilder`` does and asserts each stream only receives the fields the
referral/localization events assign to it.
"""

import io
import json
import logging
from typing import Any, Iterator

import pytest

from app.logging.context import endpoint_var, ip_var, method_var, request_id_var
from app.logging.events import Log
from app.logging.filters import AppFilter, LoggingStreams, SiemFilter
from app.logging.formatter import JsonFormatter


@pytest.fixture
def streams() -> Iterator[tuple[logging.Logger, io.StringIO, io.StringIO]]:
    app_buf, siem_buf = io.StringIO(), io.StringIO()

    app_handler = logging.StreamHandler(app_buf)
    app_handler.addFilter(AppFilter())
    app_handler.setFormatter(JsonFormatter(include_traces=False, stream=LoggingStreams.APP))

    siem_handler = logging.StreamHandler(siem_buf)
    siem_handler.addFilter(SiemFilter())
    siem_handler.setFormatter(JsonFormatter(include_traces=False, stream=LoggingStreams.SIEM))

    logger = logging.getLogger("app.test_stream_routing")
    logger.setLevel(logging.DEBUG)
    logger.handlers = [app_handler, siem_handler]
    logger.propagate = False

    tokens = [
        request_id_var.set("req-1"),
        ip_var.set("10.0.0.1"),
        endpoint_var.set("/token"),
        method_var.set("POST"),
    ]
    try:
        yield logger, app_buf, siem_buf
    finally:
        logger.handlers = []
        request_id_var.reset(tokens[0])
        ip_var.reset(tokens[1])
        endpoint_var.reset(tokens[2])
        method_var.reset(tokens[3])


def _messages(buf: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line)["message"] for line in buf.getvalue().splitlines()]


def test_registered_referral_withholds_pseudonym_hash_from_siem(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO],
) -> None:
    logger, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.REGISTERED_REFERRAL,
        "registered",
        ura_number="12345678",
        pseudonym_hash="abcd1234abcd1234",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP (stroom 2) gets ura_number + pseudonym_hash
    assert app_msg["ura_number"] == "12345678"
    assert app_msg["pseudonym_hash"] == "abcd1234abcd1234"

    # SIEM (stroom 3) gets ura_number, but NOT the pseudonym hash
    assert siem_msg["ura_number"] == "12345678"
    assert "pseudonym_hash" not in siem_msg

    # correlation metadata is retained in both
    for msg in (app_msg, siem_msg):
        assert msg["request_id"] == "req-1"
        assert msg["ip"] == "10.0.0.1"


def test_referral_access_denied_routes_to_siem_only_with_endpoint(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO],
) -> None:
    logger, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.REFERRAL_ACCESS_DENIED,
        "access denied",
        ura_number="12345678",
        resource_ura="87654321",
    )

    siem_msg = _messages(siem_buf)[0]

    # SIEM keeps ura_number + resource_ura + endpoint (endpoint comes from context)
    assert siem_msg["ura_number"] == "12345678"
    assert siem_msg["resource_ura"] == "87654321"
    assert siem_msg["endpoint"] == "/token"

    # REFERRAL_ACCESS_DENIED is SIEM-only (stroom 2 == "-")
    assert app_buf.getvalue() == ""


def test_localization_success_routes_fields_per_stream(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO],
) -> None:
    logger, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.LOCALIZATION_SUCCESS,
        "localized",
        ura_number="12345678",
        pseudonym_hash="abcd1234abcd1234",
        result_count=3,
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # APP keeps ura_number + pseudonym_hash, drops result_count
    assert app_msg["ura_number"] == "12345678"
    assert app_msg["pseudonym_hash"] == "abcd1234abcd1234"
    assert "result_count" not in app_msg

    # SIEM keeps ura_number + result_count, drops the pseudonym hash
    assert siem_msg["ura_number"] == "12345678"
    assert siem_msg["result_count"] == 3
    assert "pseudonym_hash" not in siem_msg


def test_access_request_goes_to_app_only(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO],
) -> None:
    logger, app_buf, siem_buf = streams
    Log.event(logger, Log.ACCESS_REQUEST, "access", status_code=200, duration_ms=5)

    app_msg = _messages(app_buf)[0]
    assert app_msg["endpoint"] == "/token"
    assert app_msg["method"] == "POST"
    # off-spec extras are not forwarded to the stream
    assert "status_code" not in app_msg
    assert "duration_ms" not in app_msg

    # ACCESS_REQUEST is APP-only (stroom 3 == "-")
    assert siem_buf.getvalue() == ""


def test_off_spec_extras_dropped_from_both_streams(
    streams: tuple[logging.Logger, io.StringIO, io.StringIO],
) -> None:
    logger, app_buf, siem_buf = streams
    Log.event(
        logger,
        Log.REFERRAL_DELETED,
        "deleted",
        ura_number="12345678",
        pseudonym_hash="abcd1234abcd1234",
        oin="00000001000000000001",
    )

    app_msg = _messages(app_buf)[0]
    siem_msg = _messages(siem_buf)[0]

    # ura_number is in both; pseudonym_hash only in APP; off-spec `oin` dropped from both
    assert app_msg["ura_number"] == "12345678"
    assert app_msg["pseudonym_hash"] == "abcd1234abcd1234"
    assert "oin" not in app_msg

    assert siem_msg["ura_number"] == "12345678"
    assert "pseudonym_hash" not in siem_msg
    assert "oin" not in siem_msg
