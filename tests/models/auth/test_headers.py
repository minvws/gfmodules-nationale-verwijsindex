from typing import Any, Dict
from unittest.mock import Mock

import pytest
from fastapi import Request

from app.models.auth.headers import AuthHeaders, AuthorizationRoles
from app.models.ura import UraNumber


@pytest.fixture
def auth_headers_dict(ura_number: UraNumber) -> Dict[str, Any]:
    return {
        "oin_number": "oin123",
        "source_id": "source123",
        "ura_number": ura_number.value,
        "audience": "audience",
        "authorized_role": AuthorizationRoles.CONSULTING.value,
        "scope": ["epd:read"],
        "cert_type": "oin",
    }


@pytest.fixture()
def auth_headers(ura_number: UraNumber) -> AuthHeaders:
    return AuthHeaders(  # type: ignore
        oin_number="oin123",
        source_id="source123",
        ura_number=ura_number.value,
        audience="audience",
        authorized_role=AuthorizationRoles.CONSULTING,
        scope=["epd:read"],
        cert_type="oin",
    )


@pytest.fixture()
def header_data(ura_number: UraNumber) -> Dict[str, Any]:
    return {
        "x-gf-oin-number": "oin123",
        "x-gf-source-id": "source123",
        "x-gf-ura-number": ura_number.value,
        "x-gf-audience": "audience",
        "x-gf-authorized-role": AuthorizationRoles.CONSULTING.value,
        "x-gf-scope": "epd:read",
        "x-gf-cert-type": "oin",
    }


def test_serialize_should_succeed(auth_headers: AuthHeaders, auth_headers_dict: Dict[str, Any]) -> None:
    actual = auth_headers.model_dump()

    assert actual == auth_headers_dict


def test_serialize_with_alias_should_succeed(auth_headers: AuthHeaders, header_data: Dict[str, Any]) -> None:
    expected = header_data.copy()
    expected["x-gf-scope"] = [expected["x-gf-scope"][0]]
    actual = auth_headers.model_dump(by_alias=True)

    assert actual == actual


def test_serialize_should_panic_with_invalid_rule(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["authorized_role"] = "invalid-role"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid AuthorizationRoles" in str(exec.value)


def test_deserialize_should_succeed(auth_headers_dict: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    actual = AuthHeaders(**auth_headers_dict)

    assert actual == auth_headers


def test_deserialize_with_alias_should_succeed(auth_headers: AuthHeaders, header_data: Dict[str, Any]) -> None:
    data = header_data.copy()
    data["x-gf-scope"] = [data["x-gf-scope"]]

    actual = AuthHeaders(**data)

    assert actual == auth_headers


def test_deserialize_should_panic_with_invalid_ura(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["ura_number"] = "invalid"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid URA Number in header" in str(exec.value)


def test_deserialize_should_panic_with_invalid_role(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["authorized_role"] = "invalid-role"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid AuthorizationRoles" in str(exec.value)


def test_from_request_should_succeed(header_data: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    mock_request = Mock(spec=Request)
    headers = header_data.copy()
    mock_request.headers = headers

    actual = AuthHeaders.from_request(mock_request)

    assert actual == auth_headers


def test_from_request_should_panic_with_missing_prop(
    header_data: Dict[str, Any],
) -> None:
    data = header_data.copy()
    data.pop("x-gf-oin-number")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert "x-gf-oin-number is required for AuthHeaders" in str(exec.value)


def test_from_request_or_none_should_succeed(header_data: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    mock_request = Mock(spec=Request)
    headers = header_data.copy()
    # headers["x-scope"] = auth_headers_dict["x-scope"][0]
    mock_request.headers = headers

    actual = AuthHeaders.from_request_or_none(mock_request)

    assert actual == auth_headers


def test_from_request_or_none_should_return_none_with_missing_params_in_header(
    header_data: Dict[str, Any],
) -> None:
    data = header_data.copy()
    data.pop("x-gf-oin-number")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    actual = AuthHeaders.from_request_or_none(mock_request)

    assert actual is None
