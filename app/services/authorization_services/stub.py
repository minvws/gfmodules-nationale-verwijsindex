from app.data import DataDomain, Pseudonym, UraNumber
from app.services.authorization_services.authorization_service import BaseAuthService


class StubAuthService(BaseAuthService):
    def is_authorized(
        self, ura_number: UraNumber, pseudonym: Pseudonym, data_domain: DataDomain, authorization_token: str
    ) -> bool:
        return True
