import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path
from types import TracebackType
from typing import Any, AsyncIterator

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app import container
from app.auth import get_auth_ctx
from app.config import (
    _ENVIRONMENT_CONFIG_PATH_NAME,
    _PATH,
    get_config,
)
from app.errors.handlers import (
    log_request_failure,
    register_exceptions,
)
from app.logging.config_builder import LogConfigBuilder
from app.logging.events import Log
from app.logging.middleware import RequestContextMiddleware
from app.routers.default import router as default_router
from app.routers.fhir.base import router as fhir_base_router
from app.routers.fhir.localization_list import router as fhir_list_router
from app.routers.health import router as health_router
from app.routers.localize import router as localization_router
from app.routers.registrations import router as registrations_router
from app.stats import StatsdMiddleware

logger = logging.getLogger(__name__)

_shutdown_reason: str = "graceful"


def get_uvicorn_params() -> dict[str, Any]:
    config = get_config()

    kwargs = {
        "host": config.uvicorn.host,
        "port": config.uvicorn.port,
        "reload": config.uvicorn.reload,
        "reload_delay": config.uvicorn.reload_delay,
        "reload_dirs": config.uvicorn.reload_dirs,
        "factory": True,
    }
    if (
        config.uvicorn.use_ssl
        and config.uvicorn.ssl_base_dir is not None
        and config.uvicorn.ssl_cert_file is not None
        and config.uvicorn.ssl_key_file is not None
    ):
        kwargs["ssl_keyfile"] = config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_key_file
        kwargs["ssl_certfile"] = config.uvicorn.ssl_base_dir + "/" + config.uvicorn.ssl_cert_file
    return kwargs


def run() -> None:
    uvicorn.run("app.application:create_fastapi_app", **get_uvicorn_params())


def application_init() -> None:
    setup_logging()
    _install_excepthook()
    _install_signal_handlers()


def create_fastapi_app() -> FastAPI:
    application_init()
    try:
        fastapi = setup_fastapi()
    except Exception as exc:
        Log.event(
            logger,
            Log.SYS_UNHANDLED_EXCEPTION,
            "Unhandled exception during application startup",
            exc_info=exc,
            error_type=type(exc).__name__,
        )
        raise

    return fastapi


def setup_logging() -> None:
    config = get_config()
    loglevel = config.app.loglevel.upper()
    if loglevel not in logging.getLevelNamesMapping():
        raise ValueError(f"Invalid loglevel {loglevel}")

    log_config = LogConfigBuilder(
        loglevel=loglevel,
        logging_config=config.logging,
    ).build()
    dictConfig(log_config)


def _read_version() -> str:
    path = Path(__file__).parent.parent / "version.json"
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            return str(data.get("version", "unknown"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def _install_excepthook() -> None:
    """Route uncaught exceptions through our own logging so the traceback stays in the
    debug stream only. Without this, Python prints the traceback to stderr and
    it leaks into stdout logs."""

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        global _shutdown_reason
        _shutdown_reason = "crash"
        Log.event(
            logger,
            Log.SYS_APP_CRASHED,
            "Application crashed: uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
            error_type=exc_type.__name__,
            version=_read_version(),
        )

    sys.excepthook = _hook


def _install_signal_handlers() -> None:
    """Record the shutdown reason then delegate to the previously-installed
    handler (typically uvicorn's), so we don't disrupt graceful shutdown."""

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous = signal.getsignal(sig)
        except (ValueError, OSError):
            continue

        def _make_handler(signum: int, prev: Any) -> Any:
            def _handler(s: int, frame: Any) -> None:
                global _shutdown_reason
                _shutdown_reason = f"signal:{signal.Signals(signum).name}"
                if callable(prev):
                    prev(s, frame)

            return _handler

        try:
            signal.signal(sig, _make_handler(sig, previous))
        except (ValueError, OSError):
            pass


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _shutdown_reason
    _emit_app_started()
    try:
        yield
    finally:
        if _shutdown_reason != "crash":
            Log.event(
                logger,
                Log.SYS_APP_STOPPED,
                "Application stopped",
                shutdown_reason=_shutdown_reason,
                version=_read_version(),
            )


def _emit_app_started() -> None:
    cfg = get_config()
    Log.event(
        logger,
        Log.SYS_APP_STARTED,
        "Application started",
        version=_read_version(),
        config_path=os.environ.get(_ENVIRONMENT_CONFIG_PATH_NAME, _PATH),
        crypto_service_api_enabled=cfg.crypto_service_api.enabled,
    )


def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    Log.event(
        logger,
        Log.SYS_UNHANDLED_EXCEPTION,
        "Unhandled exception",
        exc_info=exc,
        error_type=type(exc).__name__,
        endpoint=request.url.path,
        method=request.method,
    )
    log_request_failure(request, 500, exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


def setup_fastapi() -> FastAPI:
    config = get_config()

    fastapi = (
        FastAPI(
            docs_url=config.uvicorn.docs_url,
            redoc_url=config.uvicorn.redoc_url,
            title="Localisation API",
            root_path=config.uvicorn.root_path,
            lifespan=_lifespan,
        )
        if config.uvicorn.swagger_enabled
        else FastAPI(docs_url=None, redoc_url=None, lifespan=_lifespan)
    )

    container.configure()

    public_routers = [default_router, health_router]
    routers = [
        fhir_list_router,
        fhir_base_router,
        registrations_router,
        localization_router,
    ]

    for router in public_routers:
        fastapi.include_router(router)

    for router in routers:
        fastapi.include_router(router, dependencies=[Depends(get_auth_ctx)])

    register_exceptions(fastapi)

    if config.stats.enabled:
        fastapi.add_middleware(StatsdMiddleware, module_name=config.stats.module_name or "default")

    fastapi.add_middleware(RequestContextMiddleware)

    fastapi.add_exception_handler(Exception, _unhandled_exception_handler)

    return fastapi
