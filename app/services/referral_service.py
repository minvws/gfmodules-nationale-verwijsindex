import logging
from typing import List

import inject
from fastapi.exceptions import HTTPException

from app.data import Pseudonym, UraNumber
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.logger.referral_request_database_logger import ReferralRequestDatabaseLogger
from app.referral_request_payload import ReferralLoggingPayload
from app.referral_request_type import ReferralRequestType
from app.response_models.referrals import ReferralEntry
from app.services.authorization_services.authorization_interface import BaseAuthService

logger = logging.getLogger(__name__)


class ReferralService:
    @inject.autoparams()
    def __init__(self, database: Database, toestemming_service: BaseAuthService) -> None:
        self.database = database
        self.toestemming_service = toestemming_service

    def get_referrals_by_domain_and_pseudonym(
        self,
        pseudonym: Pseudonym,
        data_domain: str,
        client_ura_number: UraNumber,
        breaking_glass: bool = False,
    ) -> List[ReferralEntry]:
        """
        Method that gets all the referrals by pseudonym and data domain
        """

        with self.database.get_db_session() as session:
            # Check toestemming if requesting organization has permission
            referral_repository = session.get_repository(ReferralRepository)
            entities: List[ReferralEntity] = referral_repository.query_referrals(
                pseudonym=pseudonym, data_domain=data_domain, ura_number=None
            )
            if not entities:
                raise HTTPException(status_code=404)

            allowed_entities: List[ReferralEntry] = []

            if breaking_glass:
                # If JWT is provided an Break the Glass scenario is assumed
                logger.info(f"JWT provided, assuming Break the Glass scenario for pseudonym {pseudonym}")
                # In this case, we assume all entities are allowed as we could not ask for toestemming
                allowed_entities = [self.hydrate_referral(entity) for entity in entities]
            else:
                for entity in entities:
                    # Check toestemming if sharing organization has permission
                    otv_permission = self.toestemming_service.is_authorized(
                        pseudonym=str(pseudonym),
                        client_ura_number=str(client_ura_number),
                        dossier_keeping_ura_number=entity.ura_number,
                        dossier_keeping_org_category="V6",  # TODO hardcoded for now
                    )

                    logger.info(
                        f"Can {entity.ura_number} share data with {client_ura_number}? Toestemming-stub says: {otv_permission}"
                    )

                    if otv_permission:
                        allowed_entities.append(self.hydrate_referral(entity))

            # Returns a list of hydrated referral objects for entities where authorization is granted.
            return allowed_entities

    def add_one_referral(
        self,
        pseudonym: Pseudonym,
        data_domain: str,
        ura_number: UraNumber,
        uzi_number: str,
        request_url: str,
    ) -> ReferralEntry:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number=uzi_number,
                endpoint=request_url,
                request_type=ReferralRequestType.CREATE,
                payload={"pseudonym": str(pseudonym), "data_domain": data_domain},
            )

            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

            if (
                referral_repository.find_one(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
                is None
            ):
                referral_entity = ReferralEntity(
                    pseudonym=str(pseudonym),
                    data_domain=data_domain,
                    ura_number=str(ura_number),
                )
                return self.hydrate_referral(referral_repository.add_one(referral_entity))
            raise HTTPException(status_code=409)

    def delete_one_referral(
        self,
        pseudonym: Pseudonym,
        data_domain: str,
        ura_number: UraNumber,
        request_url: str,
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number="000000",
                endpoint=request_url,
                request_type=ReferralRequestType.DELETE,
                payload={"pseudonym": str(pseudonym), "data_domain": data_domain},
            )

            # Inject interface with DI when shared package is used (https://github.com/minvws/gfmodules-national-referral-index/issues/42)
            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

            referral_repository = session.get_repository(ReferralRepository)
            referral = referral_repository.find_one(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
            if referral is None:
                raise HTTPException(status_code=404)

            return referral_repository.delete_one(referral)

    def query_referrals(
        self,
        pseudonym: Pseudonym | None,
        data_domain: str | None,
        ura_number: UraNumber,
        request_url: str,
    ) -> List[ReferralEntry]:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number="000000",
                endpoint=request_url,
                request_type=ReferralRequestType.QUERY,
                payload={"pseudonym": str(pseudonym), "data_domain": data_domain},
            )
            # Inject interface with DI when shared package is used (https://github.com/minvws/gfmodules-national-referral-index/issues/42)
            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

            entities = referral_repository.query_referrals(
                pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number
            )
            if not entities:
                raise HTTPException(status_code=404)
            return [self.hydrate_referral(entity) for entity in entities]

    @staticmethod
    def hydrate_referral(entity: ReferralEntity) -> ReferralEntry:
        data_domain = entity.data_domain
        if data_domain is None:
            raise ValueError("Invalid data domain")

        return ReferralEntry(
            ura_number=UraNumber(entity.ura_number),
            pseudonym=Pseudonym(entity.pseudonym),
            data_domain=data_domain,
        )
