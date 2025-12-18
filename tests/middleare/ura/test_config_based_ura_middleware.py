import pytest
from fastapi.exceptions import HTTPException
from starlette.requests import Request

from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.models.ura import UraNumber


def test_authenticate_ura_should_succeed_and_return_value(
    ura_number: UraNumber,
) -> None:
    middleware = ConfigBasedUraMiddleware(config_value=ura_number)

    request = Request(
        scope={"type": "http"},
    )
    actual = middleware.authenticated_ura(request)

    assert ura_number == actual


def test_authenticate_ura_with_filter_should_succeed(
    ura_filter_service: AllowlistedUraMiddleware, ura_number: UraNumber
) -> None:
    middleware = ConfigBasedUraMiddleware(config_value=ura_number, filter_service=ura_filter_service)
    ura_filter_service.allowlist.extend([ura_number, UraNumber("00000457")])
    request = Request(
        scope={"type": "http"},
    )

    actual = middleware.authenticated_ura(request)

    assert actual == ura_number


def test_authenticate_ura_should_with_filter_should_raise_exception(
    ura_filter_service: AllowlistedUraMiddleware, ura_number: UraNumber
) -> None:
    middleware = ConfigBasedUraMiddleware(config_value=ura_number, filter_service=ura_filter_service)
    request = Request(
        scope={"type": "http"},
    )
    with pytest.raises(HTTPException):
        middleware.authenticated_ura(request)
