import pytest
from fastapi import HTTPException
from starlette.requests import Request
from uzireader.uziserver import UziServer

from app.data import UraNumber
from app.services.ura_number_finder import (
    RequestURANumberFinder,
)


def test_authenticated_ura(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {"x-proxy-ssl_client_cert": "cert-content"}

    mock_class = mocker.MagicMock(spec=UziServer)
    dic = {"SubscriberNumber": 12345679}
    mock_class.__getitem__.side_effect = dic.__getitem__

    uzi_server_creation_mock = mocker.patch.object(UziServer, "__new__", return_value=mock_class)

    actual = RequestURANumberFinder().find(request)

    assert actual == UraNumber(12345679)

    uzi_server_creation_mock.assert_called_once_with(
        UziServer,
        verify="SUCCESS",
        cert="-----BEGIN CERTIFICATE-----\ncert-content\n-----END CERTIFICATE-----",
    )
    mock_class.__getitem__.assert_called_with("SubscriberNumber")


def test_authenticated_ura_when_header_not_present(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {}

    with pytest.raises(HTTPException):
        RequestURANumberFinder().find(request)


def test_enforce_cert_newlines_with_headers(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {"x-proxy-ssl_client_cert": "cert-content"}

    cert = "-----BEGIN CERTIFICATE-----000102030405060708091011121314151617181920212223242526272829303132333435363738394041424344454647484950-----END CERTIFICATE-----"
    expected = "-----BEGIN CERTIFICATE-----\n0001020304050607080910111213141516171819202122232425262728293031\n32333435363738394041424344454647484950\n-----END CERTIFICATE-----"

    finder = RequestURANumberFinder()
    actual = finder._enforce_cert_newlines(cert)
    assert actual == expected


def test_enforce_cert_newlines_without_headers(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {"x-proxy-ssl_client_cert": "cert-content"}

    cert = "000102030405060708091011121314151617181920212223242526272829303132333435363738394041424344454647484950"
    expected = "-----BEGIN CERTIFICATE-----\n0001020304050607080910111213141516171819202122232425262728293031\n32333435363738394041424344454647484950\n-----END CERTIFICATE-----"

    finder = RequestURANumberFinder()
    actual = finder._enforce_cert_newlines(cert)
    assert actual == expected
