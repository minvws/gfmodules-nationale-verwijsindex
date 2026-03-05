import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.params import Query

from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/List")


@router.post(path="")
def create(data: LocalizationList) -> Any:
    logging.info(f"Creating {data.model_dump_json()}")


@router.get("/{id}")
def get(
    id: UUID,
) -> Any:
    logging.info(f"getting {id}")


@router.get(path="")
def query(params: Annotated[LocalizationListParams, Query()]) -> Any:
    logging.info(f"Creating {id}")


@router.delete(path="/{id}")
def delete(
    id: UUID,
) -> Any:
    logging.info(f"Delete {id}")


@router.delete(path="")
def delete_for_query(params: Annotated[LocalizationListParams, Query()]) -> Any:
    logging.info(f"Delete {id}")
