import pytest
from pydantic import BaseModel, ValidationError

from app.logging.rejections import MAX_REASON_LENGTH, summarize_reason


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


@pytest.mark.parametrize(
    "exc",
    [RuntimeError("x" * (MAX_REASON_LENGTH * 4)), _validation_error(["a"] * 1000)],
    ids=["long-message", "many-errors"],
)
def test_bounds_the_length_of_a_reason(exc: Exception) -> None:
    reason = summarize_reason(exc)

    assert len(reason) == MAX_REASON_LENGTH
    assert reason.endswith("...")


def test_keeps_a_reason_of_the_maximum_length_whole() -> None:
    message = "x" * MAX_REASON_LENGTH

    assert summarize_reason(RuntimeError(message)) == message
