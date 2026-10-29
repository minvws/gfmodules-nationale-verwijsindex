from typing import Any

from fastapi.testclient import TestClient

from app.application import setup_fastapi
from app.config import ConfigPagination, set_config
from tests.test_config import get_test_config


def _count_param(schema: dict[str, Any]) -> dict[str, Any]:
    params = schema["paths"]["/fhir/List"]["get"]["parameters"]
    return next(p for p in params if p["name"] == "_count")


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
