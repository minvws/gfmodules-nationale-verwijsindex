from typing import Any, Dict
from unittest.mock import Mock

import pytest
from fastapi import Request

from app.models.auth.headers import AuthHeaders
from app.models.ura import UraNumber


@pytest.fixture
def auth_headers_dict(ura_number: UraNumber) -> Dict[str, Any]:
    return {
        "oin": "oin123",
        "source_id": "source123",
        "ura": ura_number.value,
        "audience": "audience",
        "scope": "nvi:read",
        "cert_type": "oin",
        "organization_name": "Test Organization",
    }


@pytest.fixture()
def auth_headers(ura_number: UraNumber) -> AuthHeaders:
    return AuthHeaders(
        oin="oin123",
        source_id="source123",
        ura=ura_number.value,
        audience="audience",
        scope="nvi:read",
        cert_type="oin",
        organization_name="Test Organization",
    )


@pytest.fixture()
def header_data(ura_number: UraNumber) -> Dict[str, Any]:
    return {
        "x-gf-act-sub": "oin123",
        "x-gf-source-id": "source123",
        "x-gf-sub": ura_number.value,
        "x-gf-audience": "audience",
        "x-gf-scope": "nvi:read",
        "x-gf-cert-type": "oin",
        "x-gf-organization-name": "Test Organization",
    }


def test_serialize_should_succeed(auth_headers: AuthHeaders, auth_headers_dict: Dict[str, Any]) -> None:
    actual = auth_headers.model_dump()

    assert actual == auth_headers_dict


def test_serialize_with_alias_should_succeed(auth_headers: AuthHeaders, header_data: Dict[str, Any]) -> None:
    expected = header_data.copy()
    expected["x-gf-scope"] = [expected["x-gf-scope"][0]]
    actual = auth_headers.model_dump(by_alias=True)

    assert actual == actual


def test_deserialize_should_succeed(auth_headers_dict: Dict[str, Any], auth_headers: AuthHeaders) -> None:
    actual = AuthHeaders(**auth_headers_dict)

    assert actual == auth_headers


def test_deserialize_with_alias_should_succeed(auth_headers: AuthHeaders, header_data: Dict[str, Any]) -> None:
    data = header_data.copy()

    actual = AuthHeaders(**data)

    assert actual == auth_headers


def test_deserialize_should_panic_with_invalid_ura(
    auth_headers_dict: Dict[str, Any],
) -> None:
    data = auth_headers_dict.copy()
    data["ura"] = "invalid"

    with pytest.raises(ValueError) as exec:
        AuthHeaders(**data)

    assert "Invalid URA Number in header" in str(exec.value)


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
    data.pop("x-gf-sub")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert "x-gf-sub is required for AuthHeaders" in str(exec.value)


@pytest.mark.parametrize(
    "header_name",
    ["x-gf-act-sub", "x-gf-sub", "x-gf-audience", "x-gf-scope", "x-gf-cert-type", "x-gf-organization-name"],
)
def test_from_request_should_panic_with_any_missing_required_header(
    header_data: Dict[str, Any],
    header_name: str,
) -> None:
    data = header_data.copy()
    data.pop(header_name)
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert f"{header_name} is required for AuthHeaders" in str(exec.value)


def test_from_request_should_succeed_without_source_id(
    header_data: Dict[str, Any],
) -> None:
    """source_id is the only optional header; it is the only field declaring a default."""
    data = header_data.copy()
    data.pop("x-gf-source-id")
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    actual = AuthHeaders.from_request(mock_request)

    assert actual.source_id is None
    assert actual.oin == "oin123"


def test_from_header_should_panic_with_invalid_scope(
    header_data: Dict[str, Any],
) -> None:
    data = header_data.copy()
    data["x-gf-scope"] = "nvi:invalid-scope"
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert "Invalid scope nvi:invalid-scope" in str(exec.value)


@pytest.mark.parametrize("value", ["", " ", "\t", "  \t "])
def test_from_header_should_panic_with_empty_scope(
    header_data: Dict[str, Any],
    value: str,
) -> None:
    """An empty header used to pass validation and yield an empty scope list."""
    data = header_data.copy()
    data["x-gf-scope"] = value
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    with pytest.raises(ValueError) as exec:
        AuthHeaders.from_request(mock_request)

    assert "x-gf-scope must hold at least one scope" in str(exec.value)


def test_from_header_should_accept_multiple_scopes(
    header_data: Dict[str, Any],
) -> None:
    data = header_data.copy()
    data["x-gf-scope"] = "nvi:read nvi:create"
    mock_request = Mock(spec=Request)
    mock_request.headers = data

    actual = AuthHeaders.from_request(mock_request)

    assert actual.scope == "nvi:read nvi:create"
