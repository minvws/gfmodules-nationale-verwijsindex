import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.params import Query

from app.dependencies import (
    get_localization_list_service,
)
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.fhir.resources.data import (
    DEVICE_SYSTEM,
    EMPTY_REASON_SYSTEM,
    PSEUDONYM_SYSTEM,
    URA_SYSTEM,
    URA_SYSTEM_EXTENSION,
)
from app.models.fhir.resources.localization_list.request import (
    SUBJECT_IDENTIFIER_PARAM,
    LocalizationListParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.response import DeleteResponse, FHIRJSONResponse
from app.models.ura import UraNumber
from app.routers.dependencies import (
    require_managing_request,
    require_scope,
    require_scope_for_localization_query,
    require_source_matches_body,
    require_source_matches_query,
)
from app.services.fhir.localization_list import LocalizationListService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["FHIR"], prefix="/fhir/List")

_LIST_EXAMPLE = {
    "resourceType": "List",
    "extension": [
        {
            "valueReference": {
                "identifier": {
                    "system": URA_SYSTEM,
                    "value": "11111111",
                }
            },
            "url": URA_SYSTEM_EXTENSION,
        }
    ],
    "subject": {
        "identifier": {
            "system": PSEUDONYM_SYSTEM,
            "value": "eyJldmFsdWF0ZWRfb3V0cHV0IjoiSldFX0ZST01fUFJTIiwiYmxpbmRfZmFjdG9yIjoiQ0xJRU5UX0dFTl9CTElORF9GQUNUT1IifQ",
        }
    },
    "source": {
        "identifier": {
            "system": DEVICE_SYSTEM,
            "value": "EHR-SYS-2024-001",
        },
        "type": "Device",
    },
    "status": "current",
    "mode": "working",
    "emptyReason": {
        "coding": [
            {
                "code": "withheld",
                "system": EMPTY_REASON_SYSTEM,
            }
        ]
    },
}


@router.post(
    path="",
    status_code=201,
    response_model_exclude_none=True,
    summary="Post a new List",
    description="Create a new List resource. The code parameter for data domain is deprecated and ignored by this router.",
    response_class=FHIRJSONResponse,
    responses={
        201: {
            "description": "A List resource created",
            "content": {"application/fhir+json": {"example": _LIST_EXAMPLE}},
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def create(
    data: Annotated[
        LocalizationList,
        Body(
            media_type="application/fhir+json",
            examples=[_LIST_EXAMPLE],
        ),
    ],
    service: Annotated[LocalizationListService, Depends(get_localization_list_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.CREATE))],
    _managing: Annotated[AuthContext, Depends(require_managing_request)],
    _source: Annotated[AuthContext, Depends(require_source_matches_body)],
) -> Any:
    authorized_ura: UraNumber = ctx.claims.ura_number
    return service.create(data, authorized_ura, organization_name=ctx.claims.organization_name)


@router.get(
    "/{id}",
    status_code=200,
    response_model_exclude_none=True,
    summary="Get a List by ID",
    description="Retrieve a specific List resource based on ID",
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "List resource retrieved successfully",
            "content": {"application/fhir+json": {"example": _LIST_EXAMPLE}},
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def get(
    id: UUID,
    service: Annotated[LocalizationListService, Depends(get_localization_list_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.READ))],
) -> Any:
    authorized_ura = ctx.claims.ura_number
    return service.get(id, authorized_ura, organization_name=ctx.claims.organization_name)


@router.get(
    path="",
    response_model_exclude_none=True,
    summary="Get a Bundle of List resources with specific query params",
    description=(
        f"Retrieves a Bundle containing List resources based on query params. "
        f"Localization for a specific pseudonym can be done by specifying only {SUBJECT_IDENTIFIER_PARAM}. "
        "The code query parameter for data domain is deprecated and ignored by this router. "
        "Any other combination will return List resource specific to the URA Number of the requester"
    ),
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "List resource retrieved successfully",
            "content": {
                "application/fhir+json": {
                    "example": {
                        "resourceType": "Bundle",
                        "entry": [{"resource": _LIST_EXAMPLE}],
                    },
                },
            },
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        409: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def query(
    params: Annotated[LocalizationListParams, Query()],
    service: Annotated[LocalizationListService, Depends(get_localization_list_service)],
    ctx: Annotated[AuthContext, Depends(require_scope_for_localization_query)],
    _source: Annotated[AuthContext, Depends(require_source_matches_query)],
) -> Any:
    authorized_ura = ctx.claims.ura_number
    return service.query(params, authorized_ura, organization_name=ctx.claims.organization_name)


@router.delete(
    path="/{id}",
    response_model_exclude_none=True,
    summary="Delete a List resource by ID",
    description="Delete a specific List resource based on ID",
    status_code=201,
    responses={
        201: {"description": "Resource 1234 has been deleted successfully"},
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
    response_class=DeleteResponse,
)
def delete(
    id: UUID,
    service: Annotated[LocalizationListService, Depends(get_localization_list_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.DELETE))],
    _managing: Annotated[AuthContext, Depends(require_managing_request)],
) -> Any:
    authorized_ura = ctx.claims.ura_number
    outcome, status_code = service.delete(id, authorized_ura, organization_name=ctx.claims.organization_name)
    return FHIRJSONResponse(
        status_code=status_code,
        content=jsonable_encoder(outcome.model_dump(exclude_none=True)),
    )


@router.delete(
    path="",
    response_model_exclude_none=True,
    summary="Delete List resources based query parameters",
    description="Bulk delete for resources based on specific query parameter combinations, only resources that matches the client UraNumber would be deleted",
    status_code=201,
    responses={
        201: {"description": "Resources have been deleted successfully"},
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
    response_class=DeleteResponse,
)
def delete_for_query(
    params: Annotated[LocalizationListParams, Query()],
    service: Annotated[LocalizationListService, Depends(get_localization_list_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.DELETE))],
    _managing: Annotated[AuthContext, Depends(require_managing_request)],
    _source: Annotated[AuthContext, Depends(require_source_matches_query)],
) -> Any:
    authenticated_ura = ctx.claims.ura_number
    outcome, status_code = service.delete_by_query(
        params, authenticated_ura, organization_name=ctx.claims.organization_name
    )

    return FHIRJSONResponse(
        status_code=status_code,
        content=jsonable_encoder(outcome.model_dump(exclude_none=True)),
    )
