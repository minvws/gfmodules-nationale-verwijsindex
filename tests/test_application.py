from typing import Any

from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.config import ConfigFhir, ConfigPagination, set_config
from tests.test_config import get_test_config


def _count_param(schema: dict[str, Any]) -> dict[str, Any]:
    params = schema["paths"]["/fhir/List"]["get"]["parameters"]
    return next(p for p in params if p["name"] == "_count")


def _register_bundle_entry(schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema["paths"]["/fhir"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    entry: dict[str, Any] = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]["entry"]
    return entry


def test_openapi_shows_the_configured_page_sizes_on_count() -> None:
    config = get_test_config()
    config.pagination = ConfigPagination(default_page_size=20, max_page_size=75)
    set_config(config)

    param = _count_param(setup_fastapi().openapi())

    assert param["schema"]["default"] == 20
    assert {"type": "integer", "minimum": 1, "maximum": 75} in param["schema"]["anyOf"]
    assert "20" in param["description"]
    assert "75" in param["description"]


def test_openapi_json_endpoint_serves_the_page_sizes() -> None:
    set_config(get_test_config())

    response = TestClient(setup_fastapi()).get("/openapi.json")

    param = _count_param(response.json())
    assert param["schema"]["default"] == 50
    assert {"type": "integer", "minimum": 1, "maximum": 100} in param["schema"]["anyOf"]


def test_openapi_shows_the_configured_bundle_entry_limits() -> None:
    config = get_test_config()
    config.fhir = ConfigFhir(max_bundle_entries=7)
    set_config(config)

    entry = _register_bundle_entry(setup_fastapi().openapi())

    assert entry["minItems"] == 1
    assert entry["maxItems"] == 7
