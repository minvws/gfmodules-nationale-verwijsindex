import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

import gfmodules.logging as gflog

from app.logging.events import Log
from app.models.fhir.bundle import Bundle, BundleEntry, BundleLink
from app.models.fhir.resources.localization_list.request import (
    COUNT_PARAM,
    OFFSET_PARAM,
    LocalizationListParams,
    LocalizationListSearchParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.ura import UraNumber
from app.services.exceptions import UnauthorizedUraError
from app.services.fhir.pseudonym_token import decode_pseudonym_token
from app.services.pseudonym_referral_service import PseudonymReferralService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(
        self,
        referral_service: ReferralService,
        pseudonym_referral_service: PseudonymReferralService,
        default_page_size: int = 50,
        max_page_size: int = 100,
    ) -> None:
        self.referral_service = referral_service
        self.pseudonym_referral_service = pseudonym_referral_service
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size

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

        pseudonym = decode_pseudonym_token(data.get_encoded_pseudonym(), "List.subject.identifier.value")
        referral, created = self.pseudonym_referral_service.register(pseudonym, ura_number=ura_number, source=device)

        return LocalizationList.from_referral(referral), created

    def get(self, id: UUID, authenticated_ura: UraNumber) -> LocalizationList:
        return LocalizationList.from_referral(self.referral_service.read(id, authenticated_ura))

    def query(
        self,
        params: LocalizationListSearchParams,
        authenticated_ura: UraNumber,
        request_url: str | None = None,
    ) -> Bundle[LocalizationList]:
        """
        Search for List resources and return a single page of results.

        When `request_url` is given, the bundle links to the current, next and previous page.
        """
        page_size = min(params.count or self.default_page_size, self.max_page_size)

        if params.is_localize_params() and params.subject is not None:
            total, referrals = self.pseudonym_referral_service.localize(
                params.subject, authenticated_ura, limit=page_size, offset=params.offset
            )
        else:
            total, referrals = self.pseudonym_referral_service.query(
                authenticated_ura, pseudonym=params.subject, source=params.source, limit=page_size, offset=params.offset
            )

        bundle = Bundle(
            type="searchset",
            total=total,
            link=(
                self._page_links(request_url, page_size=page_size, offset=params.offset, total=total)
                if request_url is not None
                else None
            ),
            entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
        )

        return bundle

    @staticmethod
    def _page_links(request_url: str, page_size: int, offset: int, total: int) -> list[BundleLink]:
        def page_url(page_offset: int) -> str:
            parsed = urlparse(request_url)
            query = [
                (key, value)
                for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                if key not in (COUNT_PARAM, OFFSET_PARAM)
            ]
            query += [(COUNT_PARAM, str(page_size)), (OFFSET_PARAM, str(page_offset))]
            return urlunparse(parsed._replace(query=urlencode(query)))

        links = [BundleLink(relation="self", url=page_url(offset))]
        if offset + page_size < total:
            links.append(BundleLink(relation="next", url=page_url(offset + page_size)))
        if offset > 0:
            links.append(BundleLink(relation="previous", url=page_url(max(offset - page_size, 0))))

        return links

    def delete(
        self,
        id: UUID,
        authenticated_ura: UraNumber,
        source: str,
    ) -> OperationOutcome:
        self.referral_service.delete_by_id(id, authenticated_ura, source)
        return OperationOutcome.make_good_outcome(f"Resource {id} has been deleted successfully")

    def delete_by_query(
        self,
        params: LocalizationListParams,
        authenticated_ura: UraNumber,
        source: str,
    ) -> tuple[OperationOutcome, int]:
        deleted_count = self.pseudonym_referral_service.delete_many(
            authenticated_ura, pseudonym=params.subject, source=source
        )

        if deleted_count < 1:
            return (
                OperationOutcome.make_error_outcome(code="not-found", msg="No resources matched the given criteria"),
                404,
            )
        return (
            OperationOutcome.make_good_outcome(f"{deleted_count} resources have been deleted successfully"),
            200,
        )
