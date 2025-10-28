from app.data import Pseudonym, UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.lmr_service import LmrService
from app.services.authorization_services.stub import StubAuthService


def test_stub_authorization_succeeds() -> None:
    authorization_service = StubAuthService()
    assert issubclass(type(authorization_service), BaseAuthService)
    is_authorized = authorization_service.is_authorized(
        endpoint="https://example.com/",
        pseudonym=Pseudonym("test_pseudonym"),
        requesting_ura_number=UraNumber("1234"),
        encrypted_lmr_id="test_encrypted_lmr_id",
    )
    assert is_authorized is True


def test_lmr_authorization_succeeds(
    lmr_service: LmrService,
) -> None:
    lmr_service.api_service.do_request.return_value.json.return_value = {"authorized": True}  # type: ignore
    assert issubclass(type(lmr_service), BaseAuthService)
    is_authorized = lmr_service.is_authorized(
        endpoint="https://example.com/",
        pseudonym=Pseudonym("test_pseudonym"),
        requesting_ura_number=UraNumber("1234"),
        encrypted_lmr_id="test_encrypted_lmr_id",
    )
    assert is_authorized is True


def test_lmr_authorization_fails_because_exception(
    lmr_service: LmrService,
) -> None:
    lmr_service.api_service.do_request.side_effect = Exception("Network error")  # type: ignore
    assert issubclass(type(lmr_service), BaseAuthService)
    is_authorized = lmr_service.is_authorized(
        endpoint="https://example.com/",
        pseudonym=Pseudonym("test_pseudonym"),
        requesting_ura_number=UraNumber("1234"),
        encrypted_lmr_id="test_encrypted_lmr_id",
    )
    assert is_authorized is False
