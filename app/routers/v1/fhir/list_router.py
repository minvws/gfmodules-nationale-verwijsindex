import logging
from typing import Any
from uuid import UUID, uuid4
from app.models.v1.fhir.list_model import ListModel

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/List")


@router.post(path="")
def create(ListModel) -> Any:
    logging.info(f"Creating {id}")


@router.get("/{id}")
def get(
    id: UUID,
) -> Any:
    logging.info(f"getting {id}")
    # referral = referral_service.get_by_id(id)
    # if referral is None:
    #    raise FHIRException(
    #        status_code=404,
    #        severity="error",
    #        code="not-found",
    #        msg="Requested Record not found",
    #    )

    # return LocalizationList.from_referral(referral)


@router.get(path="")
def query(
    id: UUID,
) -> Any:
    logging.info(f"Creating {id}")


@router.delete(path="/{id}")
def delete(
    id: UUID,
) -> Any:
    logging.info(f"Delete {id}")

@router.delete(path="")
def delete_for_query(
    params
    patient_id,
) -> Any:
    logging.info(f"Delete {id}")
