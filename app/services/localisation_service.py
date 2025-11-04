from typing import List

from app.data import ReferralRequestType
from app.data_models.logging import ReferralLoggingPayload
from app.data_models.referrals import (
    CreateReferralRequest,
    DeleteReferralRequest,
    ReferralEntry,
    ReferralQuery,
    ReferralRequest,
)
from app.data_models.typing import UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.entity.logging_entity_service import LoggingEntityService
from app.services.entity.referral_entity_service import ReferralEntityService
from app.services.pseudonym_service import PseudonymService


class LocalisationService:
    def __init__(
        self,
        entity_service: ReferralEntityService,
        prs_service: PseudonymService,
        audit_logger: LoggingEntityService,
        auth_service: BaseAuthService,
    ):
        self._audit_logger = audit_logger
        self._entity_service = entity_service
        self._prs_service = prs_service
        self._auth_service = auth_service

    def create_referral(
        self,
        create_req: CreateReferralRequest,
        requesting_ura_number: UraNumber,
        request_url: str,
    ) -> ReferralEntry:
        """Creates a new referral."""
        pseudonym = self._prs_service.exchange(oprf_jwe=create_req.oprf_jwe, blind_factor=create_req.blind_factor)

        entry = self._entity_service.add_one_referral(
            pseudonym=pseudonym,
            data_domain=create_req.data_domain,
            ura_number=create_req.ura_number,
            encrypted_lmr_id=create_req.encrypted_lmr_id,
        )

        audit_entry = ReferralLoggingPayload(
            endpoint=request_url,
            requesting_uzi_number=create_req.requesting_uzi_number,
            requesting_ura_number=requesting_ura_number,
            request_type=ReferralRequestType.CREATE,
            payload={
                "pseudonym": str(pseudonym),
                "data_domain": str(create_req.data_domain),
                "ura_number": str(create_req.ura_number),
                "encrypted_lmr_id": create_req.encrypted_lmr_id,
            },
        )
        self._audit_logger.log(audit_entry)
        return entry

    def query_referrals(
        self,
        query_request: ReferralQuery,
        requesting_ura_number: UraNumber,
        request_url: str,
    ) -> List[ReferralEntry]:
        """Query referrals by optional pseudonym or optional data domain."""
        if query_request.oprf_jwe is not None and query_request.blind_factor is not None:
            pseudonym = self._prs_service.exchange(
                oprf_jwe=query_request.oprf_jwe, blind_factor=query_request.blind_factor
            )
        else:
            pseudonym = None

        referrals = self._entity_service.query_referrals(
            pseudonym=pseudonym,
            data_domain=query_request.data_domain,
            ura_number=query_request.ura_number,
        )

        audit_entry = ReferralLoggingPayload(
            endpoint=request_url,
            requesting_uzi_number=query_request.requesting_uzi_number,
            requesting_ura_number=requesting_ura_number,
            request_type=ReferralRequestType.QUERY,
            payload={
                "pseudonym": str(pseudonym),
                "data_domain": str(query_request.data_domain),
                "ura_number": str(query_request.ura_number),
            },
        )
        self._audit_logger.log(audit_entry)

        return referrals

    def delete_referral(
        self,
        delete_request: DeleteReferralRequest,
        requesting_ura_number: UraNumber,
        request_url: str,
    ) -> None:
        """Delete a referral."""
        pseudonym = self._prs_service.exchange(
            oprf_jwe=delete_request.oprf_jwe, blind_factor=delete_request.blind_factor
        )

        self._entity_service.delete_one_referral(
            pseudonym=pseudonym,
            data_domain=delete_request.data_domain,
            ura_number=delete_request.ura_number,
        )

        audit_entry = ReferralLoggingPayload(
            endpoint=request_url,
            requesting_uzi_number=delete_request.requesting_uzi_number,
            requesting_ura_number=requesting_ura_number,
            request_type=ReferralRequestType.DELETE,
            payload={
                "pseudonym": str(pseudonym),
                "data_domain": str(delete_request.data_domain),
                "ura_number": str(delete_request.ura_number),
            },
        )
        self._audit_logger.log(audit_entry)

    def query_authorized_referrals(
        self,
        referral_request: ReferralRequest,
        requesting_ura_number: UraNumber,
        requesting_uzi_number: str,
        request_url: str,
        breaking_glass: bool = False,
    ) -> List[ReferralEntry]:
        """
        Query referrals for timeline.
        For every URA obtained check Authorization in LMR.
        filter every un-authorized URA
        return with the list of authorized URAs.
        """
        pseudonym = self._prs_service.exchange(
            oprf_jwe=referral_request.oprf_jwe, blind_factor=referral_request.blind_factor
        )

        referrals = self._entity_service.query_referrals(
            pseudonym=pseudonym,
            data_domain=referral_request.data_domain,
            ura_number=None,
        )

        audit_entry = ReferralLoggingPayload(
            endpoint=request_url,
            requesting_uzi_number=requesting_uzi_number,
            requesting_ura_number=requesting_ura_number,
            request_type=ReferralRequestType.TIMELINE_REFERRAL_QUERY,
            payload={
                "pseudonym": str(pseudonym),
                "data_domain": str(referral_request.data_domain),
                "breaking_glass": breaking_glass,
            },
        )
        self._audit_logger.log(audit_entry)

        return referrals
