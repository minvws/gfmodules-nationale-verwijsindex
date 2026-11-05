import base64
import json
import logging

import pytest

from app.models.pseudonym import OprfPseudonym
from app.services.exceptions import PseudonymError
from app.services.fhir.pseudonym_token import decode_pseudonym_token
from tests.conftest import TEST_PSEUDONYM_TOKEN

FIELD = "some.field"


def _encode(data: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def test_decodes_evaluated_output_and_blind_factor() -> None:
    assert decode_pseudonym_token(TEST_PSEUDONYM_TOKEN, FIELD) == OprfPseudonym(pseudonym="JWE", oprf_key="BF")


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("not-a-valid-token!!!", id="malformed"),
        pytest.param(_encode({"something_else": "x"}), id="missing-fields"),
        pytest.param(_encode(["not", "a", "mapping"]), id="non-object"),
        pytest.param(_encode({"evaluated_output": 42, "blind_factor": "BF"}), id="non-string-field"),
    ],
)
def test_raises_pseudonym_error_on_invalid_token(token: str) -> None:
    with pytest.raises(PseudonymError, match=f"Invalid pseudonym in {FIELD}"):
        decode_pseudonym_token(token, FIELD)


def test_does_not_log_an_invalid_token(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG), pytest.raises(PseudonymError) as excinfo:
        decode_pseudonym_token("not-a-valid-token!!!", FIELD)

    assert caplog.records == []
    assert excinfo.value.__cause__ is not None
