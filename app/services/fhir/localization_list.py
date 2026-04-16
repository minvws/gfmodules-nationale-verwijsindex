import logging
from typing import Tuple
from uuid import UUID

from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(self, referral_service: ReferralService) -> None:
        self.referral_service = referral_service

    def _token_to_pseudonym(self, token: str) -> Pseudonym:
        return Pseudonym(token)

    def create(self, data: LocalizationList, authenticated_ura: UraNumber) -> LocalizationList:
        try:
            ura_number = data.get_ura()
            data_domain = data.get_data_domain()
            device = data.get_device()
        except ValueError as e:
            raise FHIRException(status_code=400, severity="error", code="invalid", msg=str(e))

        if ura_number != authenticated_ura:
            raise FHIRException(
                status_code=403,
                severity="error",
                code="security",
                msg="Registration is not linked to the authorized URA",
            )

        pseudoym = self._token_to_pseudonym(data.get_encoded_pseudonym())

        new_referral = self.referral_service.add_one(
            ura_number=ura_number,
            pseudonym=pseudoym,
            data_domain=data_domain,
            source=device,
        )

        return LocalizationList.from_referral(new_referral)

    def get(self, id: UUID, authenticated_ura: UraNumber) -> LocalizationList:
        referral = self.referral_service.get_by_id(id)
        if authenticated_ura != UraNumber(referral.ura_number):
            raise FHIRException(
                status_code=404,
                severity="error",
                code="not-found",
                msg="Resource does not exist",
            )

        return LocalizationList.from_referral(referral)

    def query(self, params: LocalizationListParams, authenticated_ura: UraNumber) -> Bundle[LocalizationList]:
        ura_number: UraNumber | None = None

        if params.empty() or params.is_localize_params() is False:
            ura_number = authenticated_ura

        pseudonym = self._token_to_pseudonym(params.subject) if params.subject else None

        referrals = self.referral_service.get_many(
            pseudonym=pseudonym,
            source=params.source,
            data_domain=DataDomain(params.code) if params.code else None,
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
            data_domain=DataDomain(params.code) if params.code else None,
            ura_number=ura_number,
        )

        return (
            OperationOutcome.make_good_outcome("Resources have been deleted successfully"),
            201,
        )
