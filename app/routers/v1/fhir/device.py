import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Request, Depends
from fastapi.params import Query

from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.resources.device.request import DeviceParams

from app import dependencies
from app.models.ura import UraNumber
from app.services.device_service import DeviceService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/Device")


@router.get("/{id}")
def get(
    id: UUID,
    request: Request,
    device_service: DeviceService = Depends(dependencies.get_device_service),
) -> Any:
    logging.info(f"getting {id}")
    requesting_ura = str(request.state.auth.ura_number)
    device_service.query(UraNumber(requesting_ura))


@router.get(path="")
def query(
    params: Annotated[DeviceParams, Query()],
    request: Request,
    device_service: DeviceService = Depends(dependencies.get_device_service),
) -> Any:
    logging.info(f"Creating {params.model_dump_json()}")
    requesting_ura = str(request.state.auth.ura_number)
    if requesting_ura != str(params.org_identifier):
        raise FHIRException(
            status_code=403,
            severity="error",
            code="forbidden",
            msg=f"Organization is forbidden to request devices for ura {request.state.auth.ura_number}",
        )

    devices = device_service.query(UraNumber(requesting_ura))
    print(devices)
