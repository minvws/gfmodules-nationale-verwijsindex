from app.models.pseudonym import OprfPseudonym
from app.services.exceptions import PseudonymError
from app.utils.fhir import decode_url_safe_token


def decode_pseudonym_token(token: str, field: str) -> OprfPseudonym:
    try:
        data = decode_url_safe_token(token)
        return OprfPseudonym(pseudonym=data["evaluated_output"], oprf_key=data["blind_factor"])
    except Exception as exc:
        raise PseudonymError(f"Invalid pseudonym in {field}") from exc
