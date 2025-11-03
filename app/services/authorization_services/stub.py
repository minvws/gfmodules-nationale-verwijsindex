from app.data import Pseudonym, UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService


class StubAuthService(BaseAuthService):
    def is_authorized(
        self,
        endpoint: str,
        pseudonym: Pseudonym,
        requesting_ura_number: UraNumber,
        encrypted_lmr_id: str,
    ) -> bool:
        return True
