import base64
import json

import pytest
from pydantic import ValidationError

from app.models.fhir.resources.data import PSEUDONYM_SYSTEM
from app.models.fhir.resources.localization_list.request import LocalizationListParams, LocalizationListSearchParams
from app.models.pseudonym import OprfPseudonym
from app.services.exceptions import PseudonymError
from tests.conftest import TEST_PSEUDONYM_TOKEN


@pytest.mark.parametrize("model", [LocalizationListParams, LocalizationListSearchParams])
@pytest.mark.parametrize("value", [TEST_PSEUDONYM_TOKEN, f"{PSEUDONYM_SYSTEM}|{TEST_PSEUDONYM_TOKEN}"])
def test_subject_is_validated_and_decoded(model: type[LocalizationListParams], value: str) -> None:
    params = model.model_validate({"subject:identifier": value})

    assert params.subject == OprfPseudonym(pseudonym="JWE", oprf_key="BF")


@pytest.mark.parametrize("value", [None, "", f"{PSEUDONYM_SYSTEM}|", "|value"])
def test_existing_subject_normalization_is_preserved(value: str | None) -> None:
    data = {} if value is None else {"subject:identifier": value}

    assert LocalizationListParams.model_validate(data).subject is None


@pytest.mark.parametrize(
    "token",
    [
        "distinctive-invalid-token!!!",
        base64.urlsafe_b64encode(json.dumps({"evaluated_output": "JWE"}).encode()).decode(),
    ],
)
def test_invalid_pseudonym_is_a_validation_error_without_input(token: str) -> None:
    with pytest.raises(ValidationError, match="subject:identifier") as error:
        LocalizationListParams.model_validate({"subject:identifier": token})

    assert token not in str(error.value)
    assert isinstance(error.value.errors()[0]["ctx"]["error"].__cause__, PseudonymError)


def test_unknown_subject_system_remains_invalid() -> None:
    with pytest.raises(ValidationError, match="Invalid subject identifier"):
        LocalizationListParams.model_validate({"subject:identifier": f"wrong-system|{TEST_PSEUDONYM_TOKEN}"})
