import pytest
from pydantic import ValidationError

from app.models.fhir.resources.data_reference.requests import DataReferenceRequestParams


def test_serialize_should_succeed() -> None:
    expected = {
        "source": "00000123",
        "pseudonym": "ps-1",
        "oprfKey": "some-key",
        "careContext": "ImagingStudy",
    }
    data = DataReferenceRequestParams(
        source="00000123",
        pseudonym="ps-1",
        oprf_key="some-key",
        care_context="ImagingStudy",
    )

    actual = data.model_dump(by_alias=True)

    assert expected == actual


def test_deserialize_should_succeed() -> None:
    expected = DataReferenceRequestParams(
        source="98765432",
        pseudonym="ps-1",
        oprf_key="some-key",
        care_context="ImagingStudy",
    )
    data = {
        "source": "98765432",
        "pseudonym": "ps-1",
        "oprfKey": "some-key",
        "careContext": "ImagingStudy",
    }

    actual = DataReferenceRequestParams.model_validate(data)

    assert expected == actual


def test_model_create_should_fail_with_str_ura() -> None:
    with pytest.raises(ValidationError):
        DataReferenceRequestParams(source="some-str-source-no-numbers")


def test_model_create_should_fail_with_incorrect_ura_number_format() -> None:
    with pytest.raises(ValidationError):
        DataReferenceRequestParams(source="123456789191982")
