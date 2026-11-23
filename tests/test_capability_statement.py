from typing import Any

import pytest

from app.models.auth.data import AuthorizationScope
from app.models.fhir.resources.localization_list.request import (
    CODE_PARAM,
    DEVICE_IDENTIFIER_PARAM,
    SUBJECT_IDENTIFIER_PARAM,
)
from app.utils.load_capability_statement import load_capability_statement


@pytest.fixture
def statement() -> dict[str, Any]:
    return load_capability_statement()


@pytest.fixture
def rest(statement: dict[str, Any]) -> dict[str, Any]:
    rest: dict[str, Any] = statement["rest"][0]
    return rest


def test_is_r4_server_capability_statement(statement: dict[str, Any]) -> None:
    assert statement["resourceType"] == "CapabilityStatement"
    assert statement["fhirVersion"] == "4.0.1"
    assert statement["kind"] == "instance"
    assert "application/fhir+json" in statement["format"]
    assert len(statement["rest"]) == 1
    assert statement["rest"][0]["mode"] == "server"


def test_only_list_resource_is_exposed(rest: dict[str, Any]) -> None:
    assert [r["type"] for r in rest["resource"]] == ["List"]


def test_list_interactions_match_routes(rest: dict[str, Any]) -> None:
    resource = rest["resource"][0]
    codes = {i["code"] for i in resource["interaction"]}
    assert codes == {"create", "read", "search-type", "delete"}
    assert resource["conditionalDelete"] == "multiple"


def test_search_params_match_query_params(rest: dict[str, Any]) -> None:
    names = {p["name"] for p in rest["resource"][0]["searchParam"]}
    expected = {p.split(":")[0] for p in (SUBJECT_IDENTIFIER_PARAM, DEVICE_IDENTIFIER_PARAM, CODE_PARAM)}
    assert names == expected


def test_bundle_endpoint_is_declared(rest: dict[str, Any]) -> None:
    assert [i["code"] for i in rest["interaction"]] == ["batch"]


def test_security_mentions_all_scopes(rest: dict[str, Any]) -> None:
    description = rest["security"]["description"]
    for scope in AuthorizationScope:
        assert scope.value in description
