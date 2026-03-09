import base64
import json
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.params import Query

from app.dependencies import get_pseudonym_service, get_referral_service
from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.resources.data import (
    DATA_DOMAIN_SYSTEM,
    DEVICE_SYSTEM,
    EMPTY_REASON_SYSTEM,
    PSEUDONYM_SYSTEM,
    URA_SYSTEM,
    URA_SYSTEM_EXTENSION,
)
from app.models.fhir.resources.localization_list.request import (
    LocalizationListParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.pseudonym import Pseudonym
from app.models.response import DeleteResponse, FHIRJSONResponse
from app.models.ura import UraNumber
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.utils.fhir import decode_url_safe_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/List")


@router.post(
    path="",
    status_code=201,
    response_model_exclude_none=True,
    summary="Post a new List",
    description="Create a new List resource",
    response_class=FHIRJSONResponse,
    responses={
        201: {
            "description": "A List resource created",
            "content": {
                "application/fhir+json": {
                    "example": {
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
                        "code": {
                            "coding": [
                                {
                                    "code": "MEDAFSPRAAK",
                                    "system": DATA_DOMAIN_SYSTEM,
                                    "display": "Medicatieafspraak",
                                }
                            ]
                        },
                    }
                }
            },
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
            example={
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
                "code": {
                    "coding": [
                        {
                            "code": "MEDAFSPRAAK",
                            "system": DATA_DOMAIN_SYSTEM,
                            "display": "Medicatieafspraak",
                        }
                    ]
                },
            },
        ),
    ],
    request: Request,
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    logging.info(f"Creating {data.model_dump_json()}")
    try:
        ura_number = data.get_ura()
        data_domain = data.get_data_domain()
        device = data.get_device()
    except ValueError as e:
        raise FHIRException(status_code=400, severity="error", code="invalid", msg=str(e))

    authorized_ura: UraNumber = request.state.auth.ura_number
    if ura_number != authorized_ura:
        raise FHIRException(
            status_code=403,
            severity="error",
            code="security",
            msg="Unauthorized access to perform CRUD operation",
        )

    try:
        encoded_token = data.get_encoded_pseudonym()
        oprf_data = decode_url_safe_token(encoded_token)
        pseudoym = pseudonym_service.exchange(
            oprf_jwe=oprf_data["evaluated_output"],
            blind_factor=oprf_data["blind_factor"],
        )
    except Exception as e:
        logger.error(f"error occurred while decoding pseudonym token: {e}")
        raise FHIRException(
            status_code=400,
            severity="error",
            code="invalid",
            msg="Invalid pseudonym in patient.identifier",
        )

    new_referral = referral_service.add_one(
        ura_number=ura_number,
        pseudonym=pseudoym,
        data_domain=data_domain,
        source=device,
    )

    return LocalizationList.from_referral(new_referral)


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
            "content": {
                "application/fhir+json": {
                    "example": {
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
                        "code": {
                            "coding": [
                                {
                                    "code": "MEDAFSPRAAK",
                                    "system": DATA_DOMAIN_SYSTEM,
                                    "display": "Medicatieafspraak",
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
        500: {"model": OperationOutcome},
    },
)
def get(
    id: UUID,
    request: Request,
    referral_service: ReferralService = Depends(get_referral_service),
) -> Any:
    referral = referral_service.get_by_id(id)
    authorized_ura: UraNumber = request.state.auth.ura_number
    if authorized_ura != UraNumber(referral.ura_number):
        raise FHIRException(
            status_code=404,
            severity="error",
            code="not-found",
            msg="Resource does not exist",
        )

    return LocalizationList.from_referral(referral)


@router.get(
    path="",
    response_model_exclude_none=True,
    summary="Get a Bundle of List resources with specific query params",
    description="Retrieves a Bundle containing List resources based on query params. Localizaiton for a specific pseudonym can be done by specifying patient.identifier and source.identifier. Any other combination will return List resource specific to the URA Number of the requester",
    response_class=FHIRJSONResponse,
    responses={
        200: {
            "description": "List resource retrieved successfully",
            "content": {
                "application/fhir+json": {
                    "example": {
                        "resourceType": "Bundle",
                        "entry": [
                            {
                                "resource": {
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
                                    "code": {
                                        "coding": [
                                            {
                                                "code": "MEDAFSPRAAK",
                                                "system": DATA_DOMAIN_SYSTEM,
                                                "display": "Medicatieafspraak",
                                            }
                                        ]
                                    },
                                }
                            }
                        ],
                    }
                }
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
    request: Request,
    params: Annotated[LocalizationListParams, Query()],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:

    code: str | None = None
    pseudonym: Pseudonym | None = None
    source: str | None = None
    ura_number: UraNumber | None = None

    if params.empty():
        ura_number = request.state.auth.ura_number

    if params.patient:
        try:
            patient_identifier = params.get_patient_identifier()
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed patient.identifier parameter",
            )

        try:
            oprf_data = decode_url_safe_token(patient_identifier.value)
            pseudonym = pseudonym_service.exchange(
                oprf_jwe=oprf_data["evaluated_output"],
                blind_factor=oprf_data["blind_factor"],
            )
        except Exception as e:
            logger.error(f"error occurred while decoding pseudonym token: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Invalid pseudonym in patient.identifier",
            )

    if params.source:
        try:
            source_identifier = params.get_source_identifier()
            source = source_identifier.value
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed source.identifier parameter",
            )

        ura_number = request.state.auth.ura_number

    if params.code:
        code = params.code

    referrals = referral_service.get_many(
        pseudonym=pseudonym,
        source=source,
        data_domain=DataDomain(code) if code else None,
        ura_number=ura_number if ura_number else None,
    )
    bundle = Bundle(
        type="searchset",
        total=len(referrals),
        entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
    )

    return bundle


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
    request: Request,
    referral_service: ReferralService = Depends(get_referral_service),
) -> Any:
    authorized_ura: UraNumber = request.state.auth.ura_number
    affected_rows = referral_service.delete_many(ura_number=authorized_ura, id=id)
    if affected_rows > 0:
        return FHIRJSONResponse(
            status_code=201,
            content=jsonable_encoder(
                OperationOutcome.make_good_outcome(f"Resource {id} have been deleted successfully").model_dump(
                    exclude_none=True
                )
            ),
        )
    else:
        return FHIRJSONResponse(
            status_code=404,
            content=jsonable_encoder(
                OperationOutcome.make_error_outcome(code="warning", msg=f"Resource {id} does not exist")
            ),
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
    request: Request,
    params: Annotated[LocalizationListParams, Query()],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    code: str | None = None
    pseudonym: Pseudonym | None = None
    source: str | None = None
    ura_number = request.state.auth.ura_number

    if params.patient:
        try:
            patient_identifier = params.get_patient_identifier()
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed patient.identifier parameter",
            )

        try:
            decoded_token = base64.urlsafe_b64decode(patient_identifier.value)
            oprf_data = json.loads(decoded_token)
            pseudonym = pseudonym_service.exchange(
                oprf_jwe=oprf_data["evaluated_output"],
                blind_factor=oprf_data["blind_factor"],
            )
        except Exception as e:
            logger.error(f"error occurred while decoding pseudonym token: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Invalid pseudonym in patient.identifier",
            )

    if params.source:
        try:
            source_identifier = params.get_source_identifier()
            source = source_identifier.value
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed source.identifier parameter",
            )

    if params.code:
        code = params.code

    referral_service.delete_many(
        pseudonym=pseudonym,
        source=source,
        data_domain=DataDomain(code) if code else None,
        ura_number=ura_number,
    )
    return FHIRJSONResponse(
        status_code=201,
        content=jsonable_encoder(
            OperationOutcome.make_good_outcome("Resources have been deleted successfully").model_dump(exclude_none=True)
        ),
    )
