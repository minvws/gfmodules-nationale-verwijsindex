import logging
from uuid import UUID

import gfmodules.logging as gflog

from app.logging.events import Log
from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.resources.localization_list.request import (
    LocalizationListParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.pseudonym import PseudonymToken
from app.models.ura import UraNumber
from app.services.exceptions import (
    NotFoundError,
    UnauthorizedUraError,
)
from app.services.pseudonym_resolver import PseudonymResolver, ResolvedPseudonym
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(
        self,
        referral_service: ReferralService,
        pseudonym_resolver: PseudonymResolver,
    ) -> None:
        self.referral_service = referral_service
        self._pseudonym_resolver = pseudonym_resolver

    def create(
        self,
        data: LocalizationList,
        authenticated_ura: UraNumber,
    ) -> tuple[LocalizationList, bool]:
        """Returns the stored List and whether it was created by this call."""
        ura_number = data.get_ura()
        device = data.get_device()

        if ura_number != authenticated_ura:
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Referral registration denied: URA mismatch",
                fields={"resource_ura": str(ura_number)},
            )
            raise UnauthorizedUraError("Registration not linked to the authorized URA")

        resolved = self._pseudonym_resolver.resolve(PseudonymToken(data.get_encoded_pseudonym()))

        referral, created = self.referral_service.add_one(
            ura_number=ura_number,
            encrypted_pseudonym=resolved.encrypted,
            source=device,
            key_id=resolved.key_id,
        )

        return LocalizationList.from_referral(referral), created

    def get(self, id: UUID, authenticated_ura: UraNumber) -> LocalizationList:
        referral = self.referral_service.get_by_id(id)
        gflog.emit(
            logger,
            Log.REFERRAL_SEARCHED_ON_ID,
            "Referral searched on id",
            fields={"pseudonym_hash": referral.pseudonym},
        )
        if authenticated_ura != UraNumber(referral.ura_number):
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Referral access denied: URA mismatch",
                fields={"resource_ura": referral.ura_number},
            )
            raise NotFoundError()

        return LocalizationList.from_referral(referral)

    def query(
        self,
        params: LocalizationListParams,
        authenticated_ura: UraNumber,
    ) -> Bundle[LocalizationList]:
        resolved: ResolvedPseudonym | None = None
        if params.subject:
            resolved = self._pseudonym_resolver.resolve(PseudonymToken(params.subject))

        if params.is_localize_params() and resolved is not None:
            referrals = self.referral_service.localize(resolved.encrypted, authenticated_ura)
        else:
            referrals = self.referral_service.get_many(
                encrypted_pseudonym=(resolved.encrypted if resolved else None),
                source=params.source,
                ura_number=authenticated_ura,
            )
            gflog.emit(
                logger,
                Log.REFERRALS_QUERIED,
                "Referrals queried",
                fields={"result_count": len(referrals)},
            )

        bundle = Bundle(
            type="searchset",
            total=len(referrals),
            entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
        )

        return bundle

    def delete(
        self,
        id: UUID,
        authenticated_ura: UraNumber,
        source: str,
    ) -> tuple[OperationOutcome, int]:
        target = self.referral_service.get_by_id(id)
        affected_rows = self.referral_service.delete_many(ura_number=authenticated_ura, source=source, id=id)
        if affected_rows > 0:
            gflog.emit(
                logger,
                Log.REFERRAL_DELETED,
                "Referral deleted",
                fields={"pseudonym_hash": target.pseudonym if target else None},
            )
            return (
                OperationOutcome.make_good_outcome(f"Resource {id} has been deleted successfully"),
                200,
            )
        else:
            return (
                OperationOutcome.make_error_outcome(code="warning", msg=f"Resource {id} does not exist"),
                404,
            )

    def delete_by_query(
        self,
        params: LocalizationListParams,
        authenticated_ura: UraNumber,
        source: str,
    ) -> tuple[OperationOutcome, int]:
        ura_number = authenticated_ura

        resolved: ResolvedPseudonym | None = None
        if params.subject:
            resolved = self._pseudonym_resolver.resolve(PseudonymToken(params.subject))

        deleted_count = self.referral_service.delete_many(
            encrypted_pseudonym=(resolved.encrypted if resolved else None),
            source=source,
            ura_number=ura_number,
        )

        if deleted_count < 1:
            return (
                OperationOutcome.make_error_outcome(code="not-found", msg="No resources matched the given criteria"),
                404,
            )
        if resolved is not None:
            gflog.emit(
                logger,
                Log.ALL_PATIENT_REFERRALS_DELETED,
                "All patient referrals deleted",
                fields={"pseudonym_hash": str(resolved.response), "deleted_count": deleted_count},
            )
        else:
            gflog.emit(
                logger,
                Log.ALL_URA_REFERRALS_DELETED,
                "All URA referrals deleted",
                fields={"deleted_count": deleted_count},
            )
        return (
            OperationOutcome.make_good_outcome(f"{deleted_count} resources have been deleted successfully"),
            200,
        )
