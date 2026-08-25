import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import gfmodules.logging as gflog
import uvicorn
from fastapi import Depends, FastAPI, Security
from fastapi.security import APIKeyHeader
from gfmodules.logging.middleware import RequestContextMiddleware

from app import container
from app.auth import get_auth_ctx
from app.config import (
    _ENVIRONMENT_CONFIG_PATH_NAME,
    _PATH,
    get_config,
)
from app.errors.handlers import register_exceptions
from app.logging.events import Log
from app.routers.default import router as default_router
from app.routers.fhir.base import router as fhir_base_router
from app.routers.fhir.localization_list import router as fhir_list_router
from app.routers.health import router as health_router
from app.routers.localize import router as localization_router
from app.routers.registrations import router as registrations_router
from app.stats import StatsdMiddleware

logger = logging.getLogger(__name__)


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
    gflog.install_excepthook(logger)
    gflog.install_signal_handlers()


def create_fastapi_app() -> FastAPI:
    application_init()
    try:
        fastapi = setup_fastapi()
    except Exception as exc:
        gflog.emit(
            logger,
            Log.SYS_UNHANDLED_EXCEPTION,
            "Unhandled exception during application startup",
            fields={"exception_type": type(exc).__name__},
            exc_info=exc,
        )
        raise

    return fastapi


def setup_logging() -> None:
    config = get_config()
    gflog.configure(config=config.logging, loglevel=config.app.loglevel, catalogue=Log)


def _read_version() -> str:
    path = Path(__file__).parent.parent / "version.json"
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            return str(data.get("version", "unknown"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with gflog.lifespan_logging(
        logger,
        version=_read_version(),
        config_path=os.environ.get(_ENVIRONMENT_CONFIG_PATH_NAME, _PATH),
        started_fields={"crypto_service_api_enabled": get_config().crypto_service_api.enabled},
    ):
        yield


def api_key_headers(document_gf_headers: bool) -> list[Any]:
    if document_gf_headers:
        headers = [
            "x-gf-audience",
            "x-gf-cert-type",
            "x-gf-organization-name",
            "x-gf-scope",
            "x-gf-sub",
            "x-gf-act-cn",
            "x-gf-act-sub",
        ]
    else:
        headers = ["Authorization"]
    return [Security(APIKeyHeader(name=header, scheme_name=header, auto_error=False)) for header in headers]


def setup_fastapi() -> FastAPI:
    config = get_config()
    fastapi = (
        FastAPI(
            docs_url=config.uvicorn.docs_url,
            redoc_url=config.uvicorn.redoc_url,
            title="Localisation API",
            root_path=config.uvicorn.root_path,
            lifespan=_lifespan,
            dependencies=api_key_headers(config.uvicorn.document_gf_headers),
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

    fastapi.add_middleware(
        RequestContextMiddleware,
        correlation_id_expected=config.logging.correlation_id_expected,
        trust_forwarded_for=config.logging.trust_forwarded_for,
    )

    return fastapi
