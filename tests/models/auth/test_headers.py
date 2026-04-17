from typing import Any, Dict
from unittest.mock import Mock

import pytest
from fastapi import Request

from app.models.auth.headers import AuthHeaders, AuthorizationRoles
from app.models.ura import UraNumber


@pytest.fixture
def auth_headers_dict(ura_number: UraNumber):
    return {
        "x-oin-number": "oin123",
        "x-source-id": "source123",
        "x-ura-number": ura_number.value,
        "x-audience": "audience",
        "x-authorized-role": AuthorizationRoles.CONSULTING.value,
    }


@pytest.fixture()
def auth_headers(ura_number: UraNumber) -> AuthHeaders:
    return AuthHeaders(
        x_oin_number="oin123",
        x_source_id="source123",
        x_ura_number=ura_number.value,
        x_audience="audience",
        x_authorized_role=AuthorizationRoles.CONSULTING,
    )


def test_serialize_should_succeed(auth_headers: AuthHeaders, auth_headers_dict: Dict[str, Any]) -> None:
    actual = auth_headers.model_dump(by_alias=True)

    assert actual == auth_headers_dict


def test_serialize_should_panic_with_invalid_rule(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["x-authorized-role"] = "invalid-role"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid AuthorizationRoles" in str(exec.value)


def test_deserialize_should_succeed(auth_headers_dict: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    actual = AuthHeaders(**auth_headers_dict)

    assert actual == auth_headers


def test_deserialize_should_panic_with_invalid_ura(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["x-ura-number"] = "invalid"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid URA Number in header" in str(exec.value)


def test_deserialize_should_panic_with_invalid_role(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["x-authorized-role"] = "invalid-role"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid AuthorizationRoles" in str(exec.value)


def test_from_request_should_succeed(auth_headers_dict: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    mock_request = Mock(spec=Request)
    mock_request.headers = auth_headers_dict

    actual = AuthHeaders.from_request(mock_request)

    assert actual == auth_headers


def test_from_request_should_panic_with_missing_prop(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data.pop("x-oin-number")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert "x-oin-number is required for AuthHeaders" in str(exec.value)


def test_from_request_or_none_should_succeed(auth_headers_dict: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    mock_request = Mock(spec=Request)
    mock_request.headers = auth_headers_dict

    actual = AuthHeaders.from_request_or_none(mock_request)

    assert actual == auth_headers


def test_from_reques_or_none_should_return_none_with_missing_params_in_header(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data.pop("x-oin-number")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    actual = AuthHeaders.from_request_or_none(mock_request)

    assert actual is None
