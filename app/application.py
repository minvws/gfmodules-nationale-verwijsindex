import logging

from fastapi import FastAPI

from app import container
from app.config import Config, load_default_config
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.info_referrals import router as info_referral_router
from app.routers.referrals import router as referral_router
from app.stats import StatsdMiddleware, setup_stats
from app.telemetry import setup_telemetry


def create_fastapi_app(config: Config | None = None) -> FastAPI:
    if not config:
        config = load_default_config()

    setup_logging(config)

    fastapi = setup_fastapi(config)

    if config.stats.enabled:
        setup_stats(config.stats)

    if config.telemetry.enabled:
        setup_telemetry(fastapi, config.telemetry)

    return fastapi


def setup_logging(config: Config) -> None:
    loglevel = logging.getLevelName(config.app.loglevel.upper())

    if isinstance(loglevel, str):
        raise ValueError(f"Invalid loglevel {loglevel.upper()}")
    logging.basicConfig(
        level=loglevel,
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )


def setup_fastapi(config: Config) -> FastAPI:
    fastapi = (
        FastAPI(
            docs_url=config.app.docs_url,
            redoc_url=config.app.redoc_url,
            title="Localisation API",
        )
        if config.app.swagger_enabled
        else FastAPI(docs_url=None, redoc_url=None)
    )
    container.configure()

    routers = [default_router, health_router, referral_router, info_referral_router]
    for router in routers:
        fastapi.include_router(router)

    if config.stats.enabled:
        fastapi.add_middleware(StatsdMiddleware, module_name=config.stats.module_name)

    return fastapi
