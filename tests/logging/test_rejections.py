import pytest
from pydantic import BaseModel, ValidationError

from app.logging.rejections import summarize_reason


class _Model(BaseModel):
    values: list[int]


def _validation_error(values: list[str]) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        _Model.model_validate({"values": values})
    return caught.value


def test_summarizes_a_validation_error_without_its_input() -> None:
    reason = summarize_reason(_validation_error(["secret-input"]))

    assert reason == "values.0: Input should be a valid integer, unable to parse string as an integer"


def test_summarizes_a_plain_exception_by_its_message() -> None:
    assert summarize_reason(RuntimeError("boom")) == "boom"
