from app.models.pseudonym import OprfPseudonym
from app.services.exceptions import PseudonymError
from app.utils.fhir import decode_url_safe_token


def decode_pseudonym_token(token: str, field: str) -> OprfPseudonym:
    try:
        data = decode_url_safe_token(token)
        return OprfPseudonym(jwe=data["evaluated_output"], blind_factor=data["blind_factor"])
    except Exception as exc:
        raise PseudonymError(f"Invalid pseudonym in {field}") from exc
