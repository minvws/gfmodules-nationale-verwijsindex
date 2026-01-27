import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app import (
    dependencies,
)
from app.db.db import Database

logger = logging.getLogger(__name__)
router = APIRouter()


def ok_or_error(value: bool) -> str:
    return "ok" if value else "error"


@router.get(
    "/health",
    summary="Health Check",
    description="health check for all dependent API services and components.",
    status_code=200,
    responses={
        200: {
            "description": "Health check completed (may contain unhealthy components)",
            "content": {
                "application/json": {
                    "examples": {
                        "all_healthy": {
                            "summary": "All services healthy",
                            "value": {
                                "status": "ok",
                                "components": {"database": "ok"},
                            },
                        },
                        "degraded": {
                            "summary": "Some services unhealthy",
                            "value": {
                                "status": "error",
                                "components": {"database": "error"},
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Unexpected error during health check execution"},
    },
    tags=["Health"],
)
def health(db: Database = Depends(dependencies.get_database)) -> JSONResponse:
    logger.info("Checking database health")

    components = {
        "database": ok_or_error(db.is_healthy()),
    }
    healthy = ok_or_error(all(value == "ok" for value in components.values()))

    return JSONResponse(content={"status": healthy, "components": components})
