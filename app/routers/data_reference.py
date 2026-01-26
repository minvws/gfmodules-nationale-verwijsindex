import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.encoders import jsonable_encoder

from app import dependencies
from app.exceptions.fhir_exception import FHIRException, OperationOutcome
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM, SOURCE_SYSTEM, SOURCE_TYPE_SYSTEM, SUBJECT_SYSTEM
from app.models.fhir.resources.data_reference.requests import DataReferenceRequestParams
from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
    NVIDataRefrenceInput,
)
from app.models.pseudonym import Pseudonym
from app.models.response import DeleteResponse, FHIRJSONResponse
from app.models.ura import UraNumber
from app.services.oauth import OAuthService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["NVI Data Reference"], prefix="/NVIDataReference")


def exchange_oprf(pseudonym_service: PseudonymService, oprf_jwe: str, blind_factor: str) -> Pseudonym:
    try:
        return pseudonym_service.exchange(oprf_jwe=oprf_jwe, blind_factor=blind_factor)
    except Exception as e:
        logger.error(f"failed to exchange pseudonym: {e}")
        raise FHIRException(
            status_code=500,
            severity="error",
            code="not-found",
            msg="Pseudonym could not be exchanged",
            expression=["NVIDataReference.subject"],
        )


@router.get(
    "",
    status_code=200,
    response_model_exclude_none=True,
    summary="Get NVIDataReference",
    description="Retrieve NVIDataReference resources based on query parameters.",
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "A bundle of NVIDataReference resources matching the query parameters.",
            "model": Bundle[NVIDataReferenceOutput],
            "content": {
                "application/fhir+json": {
                    "example": {
                        "id": "string",
                        "resourceType": "Bundle",
                        "type": "searchset",
                        "timestamp": "2026-01-26T14:46:08.945612",
                        "total": 1,
                        "entry": [
                            {
                                "resourceType": "NVIDataReference",
                                "id": "12345",
                                "meta": {"versionId": "1", "lastUpdated": "2024-12-08T14:40:00Z"},
                                "source": {"system": SOURCE_SYSTEM, "value": "90000001"},
                                "sourceType": {
                                    "coding": [
                                        {
                                            "system": SOURCE_TYPE_SYSTEM,
                                            "code": "laboratorium",
                                            "display": "Laboratorium",
                                        }
                                    ]
                                },
                                "careContext": {
                                    "coding": [
                                        {
                                            "system": CARE_CONTEXT_SYSTEM,
                                            "code": "LaboratoryTestResult",
                                            "display": "Laboratorium uitslag",
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                }
            },
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def get_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> Bundle[NVIDataReferenceOutput]:
    auth_enabled = oauth_service.enabled()
    if auth_enabled:
        req_ura = str(request.state.auth.ura_number)
        if req_ura != params.source:
            raise FHIRException(
                status_code=403,
                severity="error",
                code="forbidden",
                msg="Organization is forbidden to access requested NVIDataReference",
            )

    pseudonym: Pseudonym | None = None
    if params.pseudonym and params.oprf_key:
        pseudonym = exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe=params.pseudonym,
            blind_factor=params.oprf_key,
        )

    registrations = referral_service.get_registrations(
        ura_number=UraNumber(params.source),
        pseudonym=pseudonym,
        data_domain=DataDomain(params.care_context) if params.care_context else None,
    )
    return Bundle.from_reference_outputs(registrations)


@router.delete(
    "",
    summary="Delete NVIDataReference",
    response_model_exclude_none=True,
    response_class=DeleteResponse,
    description="Delete NVIDataReference resources based on query parameters.",
    status_code=204,
    responses={
        204: {"description": "NVIDataReference resources deleted successfully."},
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def delete_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> DeleteResponse:
    auth_enabled = oauth_service.enabled()
    if auth_enabled:
        req_ura = str(request.state.auth.ura_number)
        if req_ura != params.source:
            raise FHIRException(
                status_code=403,
                severity="error",
                code="forbidden",
                msg="Organization is forbidden to remove NVIDataReference.",
            )

    if params.pseudonym and params.oprf_key:
        pseudonym = exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe=params.pseudonym,
            blind_factor=params.oprf_key,
        )

        if params.care_context is None:
            referral_service.delete_patient_registrations(
                ura_number=UraNumber(params.source),
                pseudonym=pseudonym,
            )
        else:
            referral_service.delete_specific_registration(
                ura_number=UraNumber(params.source),
                data_domain=DataDomain(params.care_context),
                pseudonym=pseudonym,
            )

        return DeleteResponse(status_code=204)

    referral_service.delete_specific_organization(ura_number=UraNumber(params.source))
    return DeleteResponse(status_code=204)


@router.post(
    "",
    summary="Create NVIDataReference",
    response_model_exclude_none=True,
    description="Create a new NVIDataReference resource.",
    status_code=201,
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "NVIDataReference already exists.",
            "model": NVIDataReferenceOutput,
            "content": {
                "application/fhir+json": {
                    "examples": [
                        {
                            "resourceType": "NVIDataReference",
                            "id": "12345",
                            "meta": {
                                "versionId": "1",
                                "lastUpdated": "2024-12-08T14:40:00Z",
                            },
                            "source": {
                                "system": SOURCE_SYSTEM,
                                "value": "90000001",
                            },
                            "sourceType": {
                                "coding": [
                                    {
                                        "system": SOURCE_TYPE_SYSTEM,
                                        "code": "laboratorium",
                                        "display": "Laboratorium",
                                    }
                                ]
                            },
                            "careContext": {
                                "coding": [
                                    {
                                        "system": CARE_CONTEXT_SYSTEM,
                                        "code": "LaboratoryTestResult",
                                        "display": "Laboratorium uitslag",
                                    }
                                ]
                            },
                        }
                    ]
                }
            },
        },
        201: {
            "description": "NVIDataReference created successfully.",
            "model": NVIDataReferenceOutput,
            "headers": {
                "Location": {
                    "description": "URL of the created resource",
                    "schema": {"type": "string"},
                }
            },
            "content": {
                "application/fhir+json": {
                    "examples": [
                        {
                            "resourceType": "NVIDataReference",
                            "id": "12345",
                            "meta": {
                                "versionId": "1",
                                "lastUpdated": "2024-12-08T14:40:00Z",
                            },
                            "source": {
                                "system": SOURCE_SYSTEM,
                                "value": "90000001",
                            },
                            "sourceType": {
                                "coding": [
                                    {
                                        "system": SOURCE_TYPE_SYSTEM,
                                        "code": "laboratorium",
                                        "display": "Laboratorium",
                                    }
                                ]
                            },
                            "careContext": {
                                "coding": [
                                    {
                                        "system": CARE_CONTEXT_SYSTEM,
                                        "code": "LaboratoryTestResult",
                                        "display": "Laboratorium uitslag",
                                    }
                                ]
                            },
                        }
                    ]
                }
            },
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def create_reference(
    data: Annotated[
        NVIDataRefrenceInput,
        Body(
            media_type="application/fhir+json",
            examples=[
                {
                    "resourceType": "NVIDataReference",
                    "subject": {
                        "system": SUBJECT_SYSTEM,
                        "value": "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0...",
                    },
                    "source": {"system": SOURCE_SYSTEM, "value": "90000001"},
                    "sourceType": {
                        "coding": [
                            {
                                "system": SOURCE_TYPE_SYSTEM,
                                "code": "laboratorium",
                            }
                        ]
                    },
                    "careContext": {
                        "coding": [
                            {
                                "system": CARE_CONTEXT_SYSTEM,
                                "code": "LaboratoryTestResult",
                            }
                        ]
                    },
                    "oprfKey": "base64-encoded-oprf-key",
                }
            ],
        ),
    ],
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> FHIRJSONResponse:
    auth_enabled = oauth_service.enabled()
    if auth_enabled:
        req_ura: UraNumber = request.state.auth.ura_number
        if req_ura != data.get_ura_number():
            raise FHIRException(
                status_code=403,
                severity="error",
                code="forbidden",
                msg="Organization is forbidden to create NVIDataReference",
            )

    source_url = str(request.url)
    pseudonym = exchange_oprf(
        pseudonym_service=pseudonym_service,
        oprf_jwe=data.subject.value,
        blind_factor=data.oprf_key,
    )

    referral = referral_service.get_one(
        pseudonym=pseudonym,
        data_domain=data.get_data_domain(),
        ura_number=data.get_ura_number(),
    )
    if referral:
        return FHIRJSONResponse(
            status_code=200,
            content=jsonable_encoder(referral.model_dump(by_alias=True, exclude_none=True)),
        )

    new_reference = referral_service.add_one(
        pseudonym=pseudonym,
        data_domain=data.get_data_domain(),
        ura_number=data.get_ura_number(),
        organization_type=data.get_organization_type(),
        uzi_number=data.source.value,
        request_url=source_url,
    )
    return FHIRJSONResponse(
        content=jsonable_encoder(new_reference.model_dump(exclude_none=True, by_alias=True)),
        status_code=201,
        headers={"Location": source_url + f"/{new_reference.id}"},
    )


@router.get(
    "/{id}",
    status_code=200,
    response_model_exclude_none=True,
    summary="Get NVIDataReference by ID",
    description="Retrieve a specific NVIDataReference resource by its ID.",
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "NVIDataReference resource retrieved successfully.",
            "model": NVIDataReferenceOutput,
            "content": {
                "application/fhir+json": {
                    "example": {
                        "resourceType": "NVIDataReference",
                        "id": "12345",
                        "meta": {
                            "versionId": "1",
                            "lastUpdated": "2024-12-08T14:40:00Z",
                        },
                        "source": {
                            "system": SOURCE_SYSTEM,
                            "value": "90000001",
                        },
                        "sourceType": {
                            "coding": [
                                {
                                    "system": SOURCE_TYPE_SYSTEM,
                                    "code": "laboratorium",
                                    "display": "Laboratorium",
                                }
                            ]
                        },
                        "careContext": {
                            "coding": [
                                {
                                    "system": CARE_CONTEXT_SYSTEM,
                                    "code": "LaboratoryTestResult",
                                    "display": "Laboratorium uitslag",
                                }
                            ]
                        },
                    }
                }
            },
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def get_by_id(
    id: UUID,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> NVIDataReferenceOutput:
    data_reference = referral_service.get_by_id(id)
    auth_enabled = oauth_service.enabled()
    if auth_enabled:
        req_ura: UraNumber = request.state.auth.ura_number
        if req_ura != data_reference.get_ura_number():
            raise FHIRException(
                status_code=403,
                severity="error",
                code="forbidden",
                msg="Organization is forbidden to access NVIDataReference",
            )

    return data_reference


@router.delete(
    "/{id}",
    response_model_exclude_none=True,
    summary="Delete NVIDataReference by ID",
    description="Delete a specific NVIDataReference resource by its ID.",
    status_code=204,
    responses={
        204: {"description": "NVIDataReference resource deleted successfully."},
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
    response_class=DeleteResponse,
)
def delete_by_id(
    id: UUID,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> DeleteResponse:
    data_reference = referral_service.get_by_id(id)
    auth_enabled = oauth_service.enabled()
    if auth_enabled:
        req_ura: UraNumber = request.state.auth.ura_number
        if req_ura != data_reference.get_ura_number():
            raise FHIRException(
                status_code=403,
                severity="error",
                code="forbidden",
                msg="Organization is forbidden to remove NVIDataReference.",
            )

    referral_service.delete_by_id(id)
    return DeleteResponse(status_code=204)
