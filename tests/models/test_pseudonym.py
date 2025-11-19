from app.models.pseudonym import Pseudonym


def test_init_should_converts_value_to_string() -> None:
    expected = "123"
    actual = Pseudonym(123)
    assert actual.value == expected


def test_class_should_return_value_as_str() -> None:
    expected = "alias"
    actual = Pseudonym("alias")
    assert str(actual) == expected


def test_repr_format_should_succeed() -> None:
    expected = "Pseudonym(some-value)"
    actual = Pseudonym("some-value")
    assert repr(actual) == expected


def test_equality_should_succeed_with_same_value() -> None:
    pseudonym_1 = Pseudonym("John")
    pseudonym_2 = Pseudonym("John")
    assert pseudonym_1 == pseudonym_2


def test_inequality_should_succeed_with_different_value() -> None:
    pseudonym_1 = Pseudonym("Frodo")
    pseudonym_2 = Pseudonym("Sam")
    assert pseudonym_1 != pseudonym_2


def test_equality_should_return_false_when_compared_with_non_instance() -> None:
    pseudonym = Pseudonym("test")
    assert pseudonym != "test"
