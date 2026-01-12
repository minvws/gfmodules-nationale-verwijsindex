from typing import List

from app.db.db import Database
from app.db.repository.referral_repository import ReferralRepository
from app.models.fhir.resources.organization.resource import Organization


class OrganizationService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, pseudonym: str, data_domain: str, org_types: List[str] = []) -> List[Organization]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            results = repo.find(pseudonym=pseudonym, data_domain=data_domain, org_types=org_types)

        return [Organization.from_referral(r) for r in results]
