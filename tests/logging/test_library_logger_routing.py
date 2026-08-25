import logging

import gfmodules.logging as gflog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gfmodules.logging import CORRELATION_ID_HEADER, LoggingStreams
from gfmodules.logging.middleware import RequestContextMiddleware
from gfmodules.logging.testing import capture_stream

from app.logging.events import Log


def _app() -> FastAPI:
    fastapi = FastAPI()

    @fastapi.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    fastapi.add_middleware(RequestContextMiddleware, correlation_id_expected=True)
    return fastapi


class TestMissingCorrelationId:
    def test_reaches_the_app_stream_and_not_siem(self) -> None:
        internal = gflog.internal_logger_name()
        with (
            capture_stream(LoggingStreams.APP, internal) as app_stream,
            capture_stream(LoggingStreams.SIEM, internal) as siem_stream,
        ):
            TestClient(_app()).get("/ping")

        assert app_stream, f"{Log.SYS_MISSING_CORRELATION_ID.event_id} never reached the app stream"
        assert app_stream[0]["endpoint"] == "/ping"
        assert app_stream[0]["method"] == "GET"
        assert siem_stream == []

    def test_is_not_emitted_when_the_header_is_present(self) -> None:
        with capture_stream(LoggingStreams.APP, gflog.internal_logger_name()) as messages:
            TestClient(_app()).get("/ping", headers={CORRELATION_ID_HEADER: "corr-1"})

        assert messages == []


class TestUserAgent:
    def test_the_access_record_carries_the_user_agent_the_caller_sent(self) -> None:
        with capture_stream(LoggingStreams.APP, gflog.access_logger_name()) as access_stream:
            TestClient(_app()).get("/ping", headers={"User-Agent": "kube-probe/1.31"})

        assert access_stream[0]["user_agent"] == "kube-probe/1.31"

    def test_a_control_character_is_stripped_from_the_user_agent(self) -> None:
        with capture_stream(LoggingStreams.APP, gflog.access_logger_name()) as access_stream:
            TestClient(_app()).get("/ping", headers={"User-Agent": "curl/8.5.0\tprobe"})

        assert access_stream[0]["user_agent"] == "curl/8.5.0probe"


class TestTheLoggerTree:
    def test_the_library_logs_inside_the_tree_nvi_is_configured_with(self) -> None:
        assert gflog.active_logger_root() == "app"
        assert gflog.internal_logger_name() == "app.internal"
        assert gflog.access_logger_name() == "app.access"

    def test_every_nvi_logger_sits_under_that_root(self) -> None:
        assert logging.getLogger("app.application").name.startswith(gflog.active_logger_root())
