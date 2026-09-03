import asyncio
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from gfmodules.logging import CRASH, LoggingStreams
from gfmodules.logging.testing import capture_records, capture_stream, recorded_shutdown_reason
from pytest_mock import MockerFixture

from app import application
from app.config import Config, set_config
from app.logging.events import Log
from tests.test_config import get_test_config


@pytest.fixture()
def use_config() -> Config:
    cfg = get_test_config()
    set_config(cfg)
    return cfg


def _run_lifespan() -> list[Any]:
    with capture_records(application.logger.name) as captured:

        async def _exercise() -> None:
            async with application._lifespan(MagicMock()):
                pass

        asyncio.run(_exercise())
    return [entry.record for entry in captured.entries]


class TestLifespan:
    def test_logs_the_shutdown_reason_on_exit(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        stopped = [rec for rec in _run_lifespan() if rec.event_id == Log.SYS_APP_STOPPED.event_id]

        assert [rec.shutdown_reason for rec in stopped] == ["graceful"]

    def test_reports_the_signal_that_triggered_the_shutdown(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        with recorded_shutdown_reason("signal:SIGTERM"):
            stopped = [rec for rec in _run_lifespan() if rec.event_id == Log.SYS_APP_STOPPED.event_id]

        assert [rec.shutdown_reason for rec in stopped] == ["signal:SIGTERM"]

    def test_emits_no_stopped_event_after_a_crash(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="9.9.9")

        with recorded_shutdown_reason(CRASH):
            records = _run_lifespan()

        assert [rec.event_id for rec in records] == [Log.SYS_APP_STARTED.event_id]


class TestAppStarted:
    def test_reports_the_version_config_path_and_crypto_service_api(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        mocker.patch("app.application._read_version", return_value="1.2.3")

        started = [rec for rec in _run_lifespan() if rec.event_id == Log.SYS_APP_STARTED.event_id]

        assert len(started) == 1
        assert started[0].version == "1.2.3"
        assert started[0].config_path is not None
        assert started[0].crypto_service_api_enabled == use_config.crypto_service_api.enabled

    def test_the_added_field_reaches_the_app_stream(self, use_config: Config, mocker: MockerFixture) -> None:
        mocker.patch("app.application._read_version", return_value="1.2.3")

        with capture_stream(LoggingStreams.APP, application.logger.name) as messages:

            async def _exercise() -> None:
                async with application._lifespan(MagicMock()):
                    pass

            asyncio.run(_exercise())

        routed = [msg["crypto_service_api_enabled"] for msg in messages if "crypto_service_api_enabled" in msg]
        assert routed == [use_config.crypto_service_api.enabled]


class TestApplicationInit:
    def test_installs_the_logging_excepthook_and_signal_handlers(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        install_excepthook = mocker.patch("app.application.gflog.install_excepthook")
        install_signal_handlers = mocker.patch("app.application.gflog.install_signal_handlers")
        configure = mocker.patch("app.application.gflog.configure")

        application.application_init()

        configure.assert_called_once()
        install_excepthook.assert_called_once_with(application.logger)
        install_signal_handlers.assert_called_once_with()

    def test_configures_logging_with_the_nvi_catalogue(self, use_config: Config, mocker: MockerFixture) -> None:
        configure = mocker.patch("app.application.gflog.configure")

        application.setup_logging()

        configure.assert_called_once_with(
            config=use_config.logging,
            loglevel=use_config.app.loglevel,
            catalogue=Log,
        )

    def test_the_installed_excepthook_is_not_the_interpreter_default(
        self, use_config: Config, mocker: MockerFixture
    ) -> None:
        mocker.patch("app.application.gflog.configure")
        mocker.patch("app.application.gflog.install_signal_handlers")
        previous = sys.excepthook
        try:
            application.application_init()
            assert sys.excepthook is not sys.__excepthook__
        finally:
            sys.excepthook = previous


class TestStartupFailure:
    def test_logs_an_unhandled_exception_when_the_app_fails_to_build(self, mocker: MockerFixture) -> None:
        mocker.patch("app.application.application_init")
        mocker.patch("app.application.setup_fastapi", side_effect=RuntimeError("startup boom"))

        with (
            capture_records(application.logger.name) as captured,
            pytest.raises(RuntimeError),
        ):
            application.create_fastapi_app()

        records: list[Any] = [entry.record for entry in captured.entries]
        assert [record.event_id for record in records] == [Log.SYS_UNHANDLED_EXCEPTION.event_id]
        assert records[0].exception_type == "RuntimeError"
        assert records[0].exc_info is not None
