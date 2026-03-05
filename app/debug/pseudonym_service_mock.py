from app.models.pseudonym import Pseudonym
from app.services.prs.pseudonym_service import PseudonymService


class PseudonymServiceMock(PseudonymService):
    def __init__(self) -> None:
        pass

    def exchange(self, oprf_jwe: str, blind_factor: str) -> Pseudonym:
        return Pseudonym(value=f"{oprf_jwe}:{blind_factor}")
