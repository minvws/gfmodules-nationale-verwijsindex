import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.params import Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/Device")


class DeviceParams(BaseModel):
    org_identifier: str = Field(alias="organization.identifier")


@router.get("/{id}")
def get(
    id: UUID,
) -> Any:
    logging.info(f"getting {id}")


@router.get(path="")
def query(params: Annotated[DeviceParams, Query()]) -> Any:
    logging.info(f"Creating {params.model_dump_json()}")
