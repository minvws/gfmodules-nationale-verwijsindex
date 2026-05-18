import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.params import Query

from app.dependencies import get_crypto_service_api_client, get_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope, RequestedAction
from app.models.v1.registration import CreateRegistrationRequest, Registration, RegistrationList, RegistrationQueryParams
from app.services.auth.auth_context import AuthContextService
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import ConflictError, UnauthorizedActionError, UnauthorizedManagingRequestError, UnauthorizedScopeError
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1"], prefix="/v1/registrations")


@router.get("", response_model=RegistrationList)
def get_registrations(
    request: Request,
    params: Annotated[RegistrationQueryParams, Query()],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
) -> RegistrationList:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.READ not in ctx.scope:
        raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=AuthorizationScope.READ)
    if not AuthContextService.validate_action(ctx, RequestedAction.MANAGING):
        raise UnauthorizedActionError(RequestedAction.MANAGING, ctx.role)

    pseudonym = None
    if params.has_pseudonym():
        pseudonym = crypto_client.exchange(params.pseudonym, params.oprf_key)  # type: ignore[arg-type]

    referrals = referral_service.get_many(ura_number=ctx.claims.ura_number, pseudonym=pseudonym)

    if params.care_context is not None:
        referrals = [r for r in referrals if r.organization_type == params.care_context]

    registrations = [Registration.model_validate(r) for r in referrals]
    return RegistrationList(registrations=registrations, total=len(registrations))


@router.post("", status_code=201, response_model=Registration)
def create_registration(
    body: CreateRegistrationRequest,
    request: Request,
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
) -> Registration:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.CREATE not in ctx.scope:
        raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=AuthorizationScope.CREATE)
    if not AuthContextService.validate_action(ctx, RequestedAction.MANAGING):
        raise UnauthorizedActionError(RequestedAction.MANAGING, ctx.role)
    if not AuthContextService.is_managing_request(ctx):
        raise UnauthorizedManagingRequestError()

    pseudonym = crypto_client.exchange(body.pseudonym, body.oprf_key)

    try:
        referral = referral_service.add_one(
            pseudonym=pseudonym,
            ura_number=ctx.claims.ura_number,
            source=ctx.claims.source_id,  # type: ignore[arg-type]
            organization_type=body.care_context,
        )
    except ConflictError:
        raise HTTPException(status_code=409, detail="Registration already exists")

    return Registration.model_validate(referral)


@router.delete("", status_code=204)
def delete_registrations(
    request: Request,
    params: Annotated[RegistrationQueryParams, Query()],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
) -> None:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.DELETE not in ctx.scope:
        raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=AuthorizationScope.DELETE)
    if not AuthContextService.validate_action(ctx, RequestedAction.MANAGING):
        raise UnauthorizedActionError(RequestedAction.MANAGING, ctx.role)
    if not AuthContextService.is_managing_request(ctx):
        raise UnauthorizedManagingRequestError()

    pseudonym = None
    if params.has_pseudonym():
        pseudonym = crypto_client.exchange(params.pseudonym, params.oprf_key)  # type: ignore[arg-type]

    referral_service.delete_many(ura_number=ctx.claims.ura_number, pseudonym=pseudonym)
