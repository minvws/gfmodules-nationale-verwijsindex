import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import container
from app.config import Config, load_default_config
from app.dependencies import get_prs_registration_service
from app.exceptions.fhir_exception import OperationOutcome, OperationOutcomeDetail, OperationOutcomeIssue
from app.routers.data_reference import router as data_reference_router
from app.routers.default import router as default_router
from app.routers.health import router as health_router
from app.routers.info_referrals import router as info_referral_router
from app.routers.organization import router as organization_router
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

    register_at_prs()

    return fastapi


def setup_logging(config: Config) -> None:
    loglevel = logging.getLevelName(config.app.loglevel.upper())

    if isinstance(loglevel, str):
        raise ValueError(f"Invalid loglevel {loglevel.upper()}")
    logging.basicConfig(
        level=loglevel,
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )


def register_at_prs() -> None:
    prs_registration_service = get_prs_registration_service()
    prs_registration_service.register_nvi_at_prs()


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

    routers = [
        default_router,
        health_router,
        referral_router,
        info_referral_router,
        data_reference_router,
        organization_router,
    ]
    for router in routers:
        fastapi.include_router(router)

    fastapi.add_exception_handler(Exception, default_fhir_exception_handler)
    fastapi.add_exception_handler(
        RequestValidationError,
        request_validation_fhir_exception_handler,  # type: ignore
    )

    if config.stats.enabled:
        fastapi.add_middleware(StatsdMiddleware, module_name=config.stats.module_name or "default")

    return fastapi


def default_fhir_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """
    Default handler to convert generic exceptions to FHIR exceptions
    """
    outcome = OperationOutcome(
        issue=[
            OperationOutcomeIssue(
                severity="error",
                code="exception",
                details=OperationOutcomeDetail(text="An unexpected error occurred"),
                diagnostics=str(exc),
                expression=[type(exc).__name__],
            )
        ]
    )
    return JSONResponse(status_code=500, content=outcome.model_dump(by_alias=True, exclude_none=True))


def request_validation_fhir_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    issues = []

    for err in exc.errors():
        issues.append(
            OperationOutcomeIssue(
                severity="error",
                code="required" if err["type"] == "missing" else "invalid",
                diagnostics=".".join(map(str, err["loc"])) + " " + str(err["msg"]),
            ),
        )

    outcome = OperationOutcome(issue=issues)

    return JSONResponse(
        status_code=422,
        content=outcome.model_dump(by_alias=True, exclude_none=True),
    )
