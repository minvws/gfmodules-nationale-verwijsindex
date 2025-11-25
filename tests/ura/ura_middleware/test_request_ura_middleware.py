from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from uzireader.uziserver import UziServer

from app.models.ura import UraNumber
from app.ura.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.ura.ura_middleware.request_ura_middleware import RequestUraMiddleware


def test_authenticated_ura(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {"x-proxy-ssl_client_cert": "cert-content"}

    mock_class = mocker.MagicMock(spec=UziServer)
    dic = {"SubscriberNumber": 12345679}
    mock_class.__getitem__.side_effect = dic.__getitem__

    uzi_server_creation_mock = mocker.patch.object(UziServer, "__new__", return_value=mock_class)

    actual = RequestUraMiddleware().authenticated_ura(request)

    assert actual == UraNumber(12345679)

    uzi_server_creation_mock.assert_called_once_with(
        UziServer,
        verify="SUCCESS",
        cert="-----BEGIN CERTIFICATE-----\ncert-content\n-----END CERTIFICATE-----",
    )
    mock_class.__getitem__.assert_called_with("SubscriberNumber")


@patch("app.ura.ura_middleware.request_ura_middleware.verify_and_get_uzi_cert")
def test_authetnicate_with_filter_should_succeed(
    mock_verify: MagicMock,
    ura_number: UraNumber,
    ura_filter_service: AllowlistedUraMiddleware,
) -> None:
    mock_verify.return_value = ura_number
    middleware = RequestUraMiddleware(filter_service=ura_filter_service)
    ura_filter_service.allowlist.extend([UraNumber(98765432), ura_number])
    request = Request(
        scope={
            "type": "http",
            "headers": [("x-proxy-ssl_client_cert".encode(), "cert-content".encode())],
        },
    )
    actual = middleware.authenticated_ura(request)

    assert actual == ura_number


@patch("app.ura.ura_middleware.request_ura_middleware.verify_and_get_uzi_cert")
def test_authenticate_should_raise_exception_with_filter_when_ura_no_allowed(
    mock_verify: MagicMock,
    ura_number: UraNumber,
    ura_filter_service: AllowlistedUraMiddleware,
) -> None:
    mock_verify.return_value = ura_number
    middleware = RequestUraMiddleware(filter_service=ura_filter_service)
    ura_filter_service.allowlist.append(UraNumber(98765432))
    request = Request(
        scope={
            "type": "http",
            "headers": [("x-proxy-ssl_client_cert".encode(), "cert-content".encode())],
        },
    )

    with pytest.raises(HTTPException):
        middleware.authenticated_ura(request)


def test_authenticated_ura_when_header_not_present(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {}

    with pytest.raises(HTTPException):
        RequestUraMiddleware().authenticated_ura(request)
