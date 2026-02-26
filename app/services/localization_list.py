import base64
import json
import logging
from typing import Any

from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle, BundleEntry, EntryResponse
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.pseudonym import Pseudonym
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(self, referral_service: ReferralService, pseudonym_service: PseudonymService) -> None:
        self.referral_service = referral_service
        self.pseudonym_service = pseudonym_service

    def process_entry(self, entry: BundleEntry[Any], index: int) -> BundleEntry[Any]:
        if entry.request is None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.request is required")
            )

        method = entry.request.method

        if entry.resource is None:
            return BundleEntry(
                response=EntryResponse.make_validation_response(f"Bundle.entry.{index}.resource is required")
            )

        if not isinstance(entry.resource, LocalizationList):
            return BundleEntry(
                response=EntryResponse.make_validation_response(
                    msg=f"Bundle.entry.{index}.resource must be a LocalizationList",
                    code="structure",
                )
            )
        resource = entry.resource
        try:
            pseudonym = self.extract_pseudonym(resource)
        except Exception:
            return BundleEntry(
                response=EntryResponse.make_forbidden_respone("Error occurred with pseudonym decryption")
            )
        match method:
            case "POST":
                try:
                    self.referral_service.add_one(
                        pseudonym=pseudonym,
                        data_domain=resource.get_data_domain(),
                        ura_number=resource.get_ura(),
                    )
                    return BundleEntry(
                        response=EntryResponse.make_good_response(
                            f"Bundle.entry.{index}.resource has been created successfully"
                        )
                    )
                except FHIRException as e:
                    return BundleEntry(response=EntryResponse(status=str(e.status_code), outcome=e.outcome))
            case "DELETE":
                try:
                    self.referral_service.delete_one(
                        pseudonym=pseudonym,
                        data_domain=resource.get_data_domain(),
                        ura_number=resource.get_ura(),
                    )
                    return BundleEntry(
                        response=EntryResponse.make_good_response(
                            f"Bundle.entry.{index}.resource has been deleted successfully"
                        )
                    )
                except FHIRException as e:
                    return BundleEntry(response=EntryResponse(status=str(e.status_code), outcome=e.outcome))
            case _:
                return BundleEntry(
                    response=EntryResponse.make_forbidden_respone(
                        f"Bundle.entry.{index}.request.method {method} is not allowed"
                    )
                )

    def extract_pseudonym(self, resource: LocalizationList) -> Pseudonym:
        try:
            token = resource.get_encoded_pseudonym()
            decoded_token = base64.urlsafe_b64decode(token)
            data = json.loads(decoded_token)
            pseudonym = self.pseudonym_service.exchange(oprf_jwe=data["pseudonym"], blind_factor=data["oprfKey"])
            return pseudonym
        except Exception as e:
            logger.error(f"Error occurred while extracting pseudonym: {e}")
            raise e

    @staticmethod
    def validate_localization_bundle_structure(bundle: Bundle[Any]) -> bool:
        if len(bundle.entry) == 0 or bundle.entry is None:
            return False

        return True

    @staticmethod
    def validate_entry(entry: BundleEntry[Any], index: int) -> EntryResponse | None:
        if entry.resource is None:
            return EntryResponse.make_validation_response(msg=f"bundle.entry.{index}.resource is required")

        if entry.request is None:
            return EntryResponse.make_validation_response(msg=f"bundle.entry.{index}.request is required")
        return None
