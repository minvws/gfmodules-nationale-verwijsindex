from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.services.prs.exception import PseudonymError
from app.services.prs.registration_service import PrsRegistrationService

PATCHED_MODULE = "app.services.prs.registration_service.HttpService.do_request"


@patch(PATCHED_MODULE)
def test_register_organization_should_succeed(
    response: MagicMock,
    prs_registration_service: PrsRegistrationService,
) -> None:
    mock_call = MagicMock()
    mock_call.status_code = 201
    response.return_value = mock_call

    prs_registration_service._register_organization()

    response.assert_called_once_with(
        method="POST",
        sub_route="orgs",
        data={
            "ura": prs_registration_service._ura_number.value,
            "name": "nationale-verwijsindex",
            "max_key_usage": "bsn",
        },
    )


@patch(PATCHED_MODULE)
def test_register_organization_should_succeed_even_if_it_is_registered(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    mock_call = MagicMock()
    mock_call.status_code = 409
    response.return_value = mock_call

    prs_registration_service._register_organization()

    response.assert_called_once_with(
        method="POST",
        sub_route="orgs",
        data={
            "ura": prs_registration_service._ura_number.value,
            "name": "nationale-verwijsindex",
            "max_key_usage": "bsn",
        },
    )


@patch(PATCHED_MODULE)
def test_register_organization_should_raise_exception_when_status_is_in_error(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.status_code = 503
    response.side_effect = HTTPError

    with pytest.raises(PseudonymError):
        prs_registration_service._register_organization()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_organization_should_raise_exception_with_connection_error(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = ConnectionError
    with pytest.raises(PseudonymError):
        prs_registration_service._register_organization()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_organization_should_raise_exception_with_timeout(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = Timeout
    with pytest.raises(PseudonymError):
        prs_registration_service._register_organization()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_organization_should_raise_exception_with_http_error(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = HTTPError
    with pytest.raises(PseudonymError):
        prs_registration_service._register_organization()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_certificate_should_succeed(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    mock_call = MagicMock()
    mock_call.status_code = 201
    response.return_value = mock_call

    prs_registration_service._register_certificate()

    response.assert_called_once_with(
        method="POST",
        sub_route="register/certificate",
        data={"scope": ["nationale-verwijsindex"]},
    )


@patch(PATCHED_MODULE)
def test_register_certificate_should_succeed_even_if_it_is_registered(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    mock_call = MagicMock()
    mock_call.status_code = 409
    response.return_value = mock_call

    prs_registration_service._register_certificate()

    response.assert_called_once_with(
        method="POST",
        sub_route="register/certificate",
        data={"scope": ["nationale-verwijsindex"]},
    )


@patch(PATCHED_MODULE)
def test_register_certificate_should_raise_exception_with_error_status_code(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.status_code = 503
    response.side_effect = HTTPError
    with pytest.raises(PseudonymError):
        prs_registration_service._register_certificate()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_certificate_should_raise_exception_with_connection_error(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = ConnectionError
    with pytest.raises(PseudonymError):
        prs_registration_service._register_certificate()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_certificate_should_raise_exception_with_timeout(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = Timeout
    with pytest.raises(PseudonymError):
        prs_registration_service._register_certificate()
        response.assert_called_once()


@patch(PATCHED_MODULE)
def test_register_certificate_should_raise_exception_with_http_error(
    response: MagicMock, prs_registration_service: PrsRegistrationService
) -> None:
    response.side_effect = HTTPError
    with pytest.raises(PseudonymError):
        prs_registration_service._register_certificate()
        response.assert_called_once()
