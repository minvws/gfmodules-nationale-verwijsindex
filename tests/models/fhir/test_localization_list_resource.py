from typing import Any

import pytest

from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.services.exceptions import InvalidResourceError
from tests.conftest import make_list_resource


def _with(path: tuple[str | int, ...], value: str) -> LocalizationList:
    body = make_list_resource().model_dump(by_alias=True, exclude_none=True, mode="json")
    node: Any = body
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return LocalizationList.model_validate(body)


URA = ("extension", 0, "valueReference", "identifier")


def test_get_ura_rejects_a_missing_ura_identifier() -> None:
    with pytest.raises(InvalidResourceError, match="Missing identifier"):
        _with((*URA, "system"), "urn:wrong").get_ura()


def test_get_ura_rejects_an_invalid_ura() -> None:
    with pytest.raises(InvalidResourceError, match="Invalid URA in List.extension"):
        _with((*URA, "value"), "not-a-ura").get_ura()


def test_get_encoded_pseudonym_rejects_a_wrong_system() -> None:
    with pytest.raises(InvalidResourceError, match="List.subject.identifier.system"):
        _with(("subject", "identifier", "system"), "urn:wrong").get_encoded_pseudonym()


def test_get_encoded_pseudonym_rejects_a_missing_subject() -> None:
    with pytest.raises(InvalidResourceError, match="List.subject is required"):
        make_list_resource(pseudonym=None).get_encoded_pseudonym()


def test_get_device_rejects_a_wrong_system() -> None:
    with pytest.raises(InvalidResourceError, match="List.source.identifier"):
        _with(("source", "identifier", "system"), "urn:wrong").get_device()
