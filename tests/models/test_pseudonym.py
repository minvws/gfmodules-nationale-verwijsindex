from app.models.pseudonym import EncryptedPseudonym


def test_init_should_converts_value_to_string() -> None:
    expected = "456123"
    actual = EncryptedPseudonym(encrypted_data=123, iv=456)
    assert actual.value == expected


def test_class_should_return_value_as_str() -> None:
    data = "alias"
    iv = "some-128-bit-iv"
    expected = iv + data
    actual = EncryptedPseudonym(data, iv)
    assert str(actual) == expected


def test_repr_format_should_succeed() -> None:
    data = "some-encrypted-data"
    iv = "some-128-bit-iv"
    expected = f"EncryptedPseudonym({iv + data})"
    actual = EncryptedPseudonym(data, iv)
    assert repr(actual) == expected


def test_equality_should_succeed_with_same_value() -> None:
    pseudonym_1 = EncryptedPseudonym("John", "Doe")
    pseudonym_2 = EncryptedPseudonym("John", "Doe")
    assert pseudonym_1 == pseudonym_2


def test_inequality_should_succeed_with_different_value() -> None:
    pseudonym_1 = EncryptedPseudonym("Frodo", "Baggins")
    pseudonym_2 = EncryptedPseudonym("Sam", "Gamgee")
    assert pseudonym_1 != pseudonym_2


def test_equality_should_return_false_when_compared_with_non_instance() -> None:
    pseudonym = EncryptedPseudonym("test", "mock")
    assert pseudonym != "test"
