from app.data import UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService


class StubAuthService(BaseAuthService):
    def is_authorized(
        self,
        client_ura_number: UraNumber,
        encrypted_lmr_id: str,
        lmr_endpoint: str,
    ) -> bool:
        return True
