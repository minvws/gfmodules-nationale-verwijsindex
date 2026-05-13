import logging
from typing import Tuple
from uuid import UUID

from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.resources.localization_list.request import (
    SUBJECT_IDENTIFIER_PARAM,
    LocalizationListParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import (
    NotFoundError,
    PseudonymError,
    UnauthorizedUraError,
)
from app.services.referral_service import ReferralService
from app.utils.fhir import decode_url_safe_token

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(self, referral_service: ReferralService, crypto_client: CryptoServiceApiClient) -> None:
        self.referral_service = referral_service
        self._crypto_client = crypto_client

    def _token_to_pseudonym(self, token: str) -> Pseudonym:
        try:
            data = decode_url_safe_token(token)
            return self._crypto_client.decrypt_and_hash(
                data["evaluated_output"],
                data["blind_factor"],
            )
        except Exception as e:
            logger.error(f"error occurred while decoding pseudonym token: {e}")
            raise PseudonymError(f"Invalid pseudonym in {SUBJECT_IDENTIFIER_PARAM}")

    def create(self, data: LocalizationList, authenticated_ura: UraNumber) -> LocalizationList:
        ura_number = data.get_ura()
        device = data.get_device()

        if ura_number != authenticated_ura:
            raise UnauthorizedUraError("Registration not linked to the authorized URA")

        pseudonym = self._token_to_pseudonym(data.get_encoded_pseudonym())

        new_referral = self.referral_service.add_one(
            ura_number=ura_number,
            pseudonym=pseudonym,
            source=device,
        )

        return LocalizationList.from_referral(new_referral)

    def get(self, id: UUID, authenticated_ura: UraNumber) -> LocalizationList:
        referral = self.referral_service.get_by_id(id)
        if authenticated_ura != UraNumber(referral.ura_number):
            raise NotFoundError()

        return LocalizationList.from_referral(referral)

    def query(self, params: LocalizationListParams, authenticated_ura: UraNumber) -> Bundle[LocalizationList]:
        ura_number: UraNumber | None = None

        if params.empty() or params.is_localize_params() is False:
            ura_number = authenticated_ura

        pseudonym = self._token_to_pseudonym(params.subject) if params.subject else None

        referrals = self.referral_service.get_many(
            pseudonym=pseudonym,
            source=params.source,
            ura_number=ura_number,
        )
        bundle = Bundle(
            type="searchset",
            total=len(referrals),
            entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
        )

        return bundle

    def delete(self, id: UUID, authenticated_ura: UraNumber) -> Tuple[OperationOutcome, int]:
        affected_rows = self.referral_service.delete_many(ura_number=authenticated_ura, id=id)
        if affected_rows > 0:
            return (
                OperationOutcome.make_good_outcome(f"Resource {id} has been deleted successfully"),
                201,
            )
        else:
            return (
                OperationOutcome.make_error_outcome(code="warning", msg=f"Resource {id} does not exist"),
                404,
            )

    def delete_by_query(
        self, params: LocalizationListParams, authenticated_ura: UraNumber
    ) -> Tuple[OperationOutcome, int]:
        ura_number = authenticated_ura

        pseudonym = self._token_to_pseudonym(params.subject) if params.subject else None

        self.referral_service.delete_many(
            pseudonym=pseudonym,
            source=params.source,
            ura_number=ura_number,
        )

        return (
            OperationOutcome.make_good_outcome("Resources have been deleted successfully"),
            201,
        )
