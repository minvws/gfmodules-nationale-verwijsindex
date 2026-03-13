import base64
import json
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
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.utils.fhir import decode_url_safe_token

logger = logging.getLogger(__name__)


class LocalizationListService:
    def __init__(self, referral_service: ReferralService, pseudonym_service: PseudonymService) -> None:
        self.referral_service = referral_service
        self.pseudonym_service = pseudonym_service

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

        try:
            encoded_token = data.get_encoded_pseudonym()
            oprf_data = decode_url_safe_token(encoded_token)
            pseudoym = self.pseudonym_service.exchange(
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
        code: str | None = None
        pseudonym: Pseudonym | None = None
        source: str | None = None
        ura_number: UraNumber | None = None

        if params.empty() or params.is_localize_params() is False:
            ura_number = authenticated_ura

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
                pseudonym = self.pseudonym_service.exchange(
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

        referrals = self.referral_service.get_many(
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

    def delete(self, id: UUID, authenticated_ura: UraNumber) -> Tuple[OperationOutcome, int]:
        affected_rows = self.referral_service.delete_many(ura_number=authenticated_ura, id=id)
        if affected_rows > 0:
            return (
                OperationOutcome.make_good_outcome(f"Resource {id} have been deleted successfully"),
                201,
            )
        else:
            return (
                OperationOutcome.make_error_outcome(code="warning", msg=f"Resource {id} does not exist"),
                404,
            )

    def delete_by_query(self, params: LocalizationListParams, authenticated_ura: UraNumber) -> OperationOutcome:
        code: str | None = None
        pseudonym: Pseudonym | None = None
        source: str | None = None
        ura_number = authenticated_ura

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
                pseudonym = self.pseudonym_service.exchange(
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

        self.referral_service.delete_many(
            pseudonym=pseudonym,
            source=source,
            data_domain=DataDomain(code) if code else None,
            ura_number=ura_number,
        )

        return OperationOutcome.make_good_outcome("Resources have beend deleted successfully")
