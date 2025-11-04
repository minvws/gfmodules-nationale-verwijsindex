import base64
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from app.data_models.typing import Pseudonym
from app.services.api_service import HttpService
from app.services.pseudonym_service import PseudonymError, PseudonymService

PATCHED_VERIFY_CERT = "app.services.pseudonym_service.verify_and_get_uzi_cert"


@patch("app.services.pseudonym_service.pyoprf.unblind")
def test_exchange_succeeds(
    mock_unblind: MagicMock,
    prs_service: PseudonymService,
) -> None:
    prs_service._decrypt_service.decrypt_jwe = MagicMock(  # type: ignore
        return_value={"subject": "pseudonym:eval:dGVzdA=="}  # base64("test")
    )
    mock_unblind.return_value = b"unblinded_result"

    oprf_jwe = "valid_oprf_jwe"
    blind_factor = base64.urlsafe_b64encode(b"blind_factor").decode()

    result = prs_service.exchange(oprf_jwe=oprf_jwe, blind_factor=blind_factor)

    assert isinstance(result, Pseudonym)
    prs_service._decrypt_service.decrypt_jwe.assert_called_once_with(oprf_jwe)
    mock_unblind.assert_called_once()
    assert result.value == base64.urlsafe_b64encode(b"unblinded_result").decode()


def test_exchange_raises_for_invalid_subject(
    prs_service: PseudonymService,
) -> None:
    prs_service._decrypt_service.decrypt_jwe = MagicMock(  # type: ignore
        return_value={"subject": "invalid:subject"}
    )

    with pytest.raises(PseudonymError) as exc:
        prs_service.exchange(oprf_jwe="test_jwe", blind_factor="test_factor")

    assert "invalid subject" in str(exc.value) or "JWE is invalid" in str(exc.value)


@patch("builtins.open", new_callable=mock_open, read_data="test_cert_data")
@patch.object(PseudonymService, "_register_organization")
@patch.object(PseudonymService, "_register_certificate")
def test_register_nvi_at_prs_succeeds(
    mock_register_cert: MagicMock,
    mock_register_org: MagicMock,
    mock_file: MagicMock,
    prs_service: PseudonymService,
) -> None:
    prs_service.register_nvi_at_prs()

    mock_file.assert_called_once_with(prs_service._mtls_cert, "r")
    mock_register_org.assert_called_once_with("test_cert_data")
    mock_register_cert.assert_called_once()


@patch(PATCHED_VERIFY_CERT)
def test_register_organization_succeeds(
    mock_verify_cert: MagicMock,
    prs_service: PseudonymService,
) -> None:
    mock_ura = MagicMock(value="12345678")
    mock_verify_cert.return_value = mock_ura

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))
    prs_service._api_service.do_request.return_value = mock_response  # type: ignore

    prs_service._register_organization("test_cert_data")

    mock_verify_cert.assert_called_once_with(cert="test_cert_data")
    prs_service._api_service.do_request.assert_called_once_with(  # type: ignore
        method="POST",
        json={"ura": "12345678", "name": "nvi", "max_key_usage": "bsn"},
        sub_route="orgs",
    )


@patch(PATCHED_VERIFY_CERT)
def test_register_organization_succeeds_already_exists(
    mock_verify_cert: MagicMock, prs_service: PseudonymService
) -> None:
    mock_ura = MagicMock(value="12345678")
    mock_verify_cert.return_value = mock_ura

    mock_response = MagicMock(status_code=409)
    err = requests.RequestException()
    err.response = mock_response
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))
    prs_service._api_service.do_request.side_effect = err  # type: ignore

    prs_service._register_organization("test_cert_data")
    prs_service._api_service.do_request.assert_called_once()  # type: ignore


@patch(PATCHED_VERIFY_CERT)
def test_register_organization_raises_network_error(mock_verify_cert: MagicMock, prs_service: PseudonymService) -> None:
    mock_ura = MagicMock(value="12345678")
    mock_verify_cert.return_value = mock_ura
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))

    prs_service._api_service.do_request.side_effect = requests.RequestException("Network error")  # type: ignore

    with pytest.raises(PseudonymError) as exc:
        prs_service._register_organization("test_cert_data")

    assert "Failed to register organization" in str(exc.value)


def test_register_certificate_succeeds(prs_service: PseudonymService) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))
    prs_service._api_service.do_request.return_value = mock_response  # type: ignore

    prs_service._register_certificate()

    prs_service._api_service.do_request.assert_called_once_with(  # type: ignore
        method="POST",
        json={"scope": ["nvi"]},
        sub_route="register/certificate",
    )


def test_register_certificate_already_exists(prs_service: PseudonymService) -> None:
    mock_response = MagicMock(status_code=409)
    err = requests.RequestException()
    err.response = mock_response
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))
    prs_service._api_service.do_request.side_effect = err  # type: ignore

    prs_service._register_certificate()
    prs_service._api_service.do_request.assert_called_once()  # type: ignore


def test_register_certificate_fails_with_network_error(prs_service: PseudonymService) -> None:
    prs_service.__setattr__("_api_service", MagicMock(spec=HttpService))
    prs_service._api_service.do_request.side_effect = requests.RequestException("Network error")  # type: ignore

    with pytest.raises(PseudonymError) as exc:
        prs_service._register_certificate()

    assert "Failed to register certificate" in str(exc.value)
