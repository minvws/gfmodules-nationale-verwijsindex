from unittest.mock import MagicMock, patch

import pytest

from app.data import UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.lmr_service import LmrService
from app.services.authorization_services.stub import StubAuthService


@patch("app.services.authorization_services.lmr_service.request")
def test_lmr_auth_service_is_authorized(
    mock_request: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"authorized": True}
    mock_request.return_value = mock_response
    auth_service = LmrService()
    assert issubclass(type(auth_service), BaseAuthService)
    assert (
        auth_service.is_authorized(
            client_ura_number=UraNumber("12345"), encrypted_lmr_id="some_encrypted_id", lmr_endpoint="some_endpoint"
        )
        is True
    )


@patch("app.services.authorization_services.lmr_service.request")
def test_lmr_auth_service_is_not_authorized(
    mock_request: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"authorized": False}
    mock_request.return_value = mock_response
    auth_service = LmrService()
    assert issubclass(type(auth_service), BaseAuthService)
    assert (
        auth_service.is_authorized(
            client_ura_number=UraNumber("12345"), encrypted_lmr_id="some_encrypted_id", lmr_endpoint="some_endpoint"
        )
        is False
    )


def test_stub_auth_service_is_authorized():
    auth_service = StubAuthService()
    assert issubclass(type(auth_service), BaseAuthService)
    assert (
        auth_service.is_authorized(
            client_ura_number=UraNumber("12345"), encrypted_lmr_id="some_encrypted_id", lmr_endpoint="some_endpoint"
        )
        is True
    )


def test_stub_auth_service_will_fail_if_argument_not_given():
    auth_service = StubAuthService()
    assert issubclass(type(auth_service), BaseAuthService)
    with pytest.raises(TypeError) as excinfo:
        auth_service.is_authorized(  # type: ignore
            client_ura_number=UraNumber("12345"),
        )
    assert "missing 2 required positional arguments" in str(excinfo.value)
