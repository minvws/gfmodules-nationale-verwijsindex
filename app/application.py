import logging
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import container
from app.auth import get_auth_ctx
from app.config import get_config
from app.dependencies import get_prs_registration_service
from app.exceptions.fhir_exception import (
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)
from app.routers.data_reference import router as data_reference_router
from app.routers.default import router as default_router
from app.routers.fhir import router as fhir_router
from app.routers.health import router as health_router
from app.routers.organization import router as organization_router
from app.routers.patient import router as patient_router
from app.stats import StatsdMiddleware


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


def create_fastapi_app() -> FastAPI:
    setup_logging()
    fastapi = setup_fastapi()
    register_at_prs()

    return fastapi


def setup_logging() -> None:
    config = get_config()
    if config.app.loglevel.upper() not in logging.getLevelNamesMapping():
        raise ValueError(f"Invalid loglevel {config.app.loglevel.upper()}")
    logging.basicConfig(
        level=logging.getLevelNamesMapping()[config.app.loglevel.upper()],
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )


def register_at_prs() -> None:
    prs_registration_service = get_prs_registration_service()
    prs_registration_service.register_nvi_at_prs()


def setup_fastapi() -> FastAPI:
    config = get_config()

    fastapi = (
        FastAPI(
            docs_url=config.uvicorn.docs_url,
            redoc_url=config.uvicorn.redoc_url,
            title="Localisation API",
        )
        if config.uvicorn.swagger_enabled
        else FastAPI(docs_url=None, redoc_url=None)
    )

    container.configure()
    # TODO: move patient to private router
    public_routers = [default_router, health_router, fhir_router]
    for router in public_routers:
        fastapi.include_router(router)

    routers = [data_reference_router, organization_router, patient_router]
    for router in routers:
        fastapi.include_router(router, dependencies=[Depends(get_auth_ctx)])

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
                expression=[type(exc).__name__],
            )
        ]
    )
    return JSONResponse(
        status_code=500,
        content=outcome.model_dump(by_alias=True, exclude_none=True),
        headers={"Content-Type": "application/fhir+json"},
    )


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
                details=OperationOutcomeDetail(text=".".join(map(str, err["loc"])) + " " + str(err["msg"])),
            ),
        )

    outcome = OperationOutcome(issue=issues)

    return JSONResponse(
        status_code=422,
        content=outcome.model_dump(by_alias=True, exclude_none=True),
        headers={"Content-Type": "application/fhir+json"},
    )
