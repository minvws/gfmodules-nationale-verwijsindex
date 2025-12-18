import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura.request_ura_middleware import RequestUraMiddleware
from app.models.ura import UraNumber


def test_authenticated_ura_should_succeed(
    certificate_str: str,
    ura_number: UraNumber,
) -> None:
    middleware = RequestUraMiddleware()
    request = Request(
        scope={
            "type": "http",
            "headers": [("x-proxy-ssl_client_cert".encode(), certificate_str.encode())],
        },
    )

    actual = middleware.authenticated_ura(request)

    assert actual == ura_number


def test_authenticate_ura_should_succeed_with_filter(
    certificate_str: str,
    ura_number: UraNumber,
    ura_filter_service: AllowlistedUraMiddleware,
) -> None:
    middleware = RequestUraMiddleware(filter_service=ura_filter_service)
    ura_filter_service.allowlist.extend([ura_number])
    request = Request(
        scope={
            "type": "http",
            "headers": [("x-proxy-ssl_client_cert".encode(), certificate_str.encode())],
        },
    )

    actual = middleware.authenticated_ura(request)

    assert actual == ura_number


def test_authenticate_should_raise_exception_with_filter_when_ura_no_allowed(
    certificate_str: str,
    ura_number: UraNumber,
    ura_filter_service: AllowlistedUraMiddleware,
) -> None:
    middleware = RequestUraMiddleware(filter_service=ura_filter_service)
    request = Request(
        scope={
            "type": "http",
            "headers": [("x-proxy-ssl_client_cert".encode(), certificate_str.encode())],
        },
    )
    with pytest.raises(HTTPException) as exec:
        middleware.authenticated_ura(request)

    assert exec.value.status_code == 403


def test_authenticated_ura_when_header_not_present(mocker):
    request = mocker.MagicMock(spec=Request)
    request.headers = {}

    with pytest.raises(HTTPException) as exec:
        RequestUraMiddleware().authenticated_ura(request)

    assert exec.value.status_code == 401
