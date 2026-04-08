import pytest

from app.models.fhir.elements import CodeableConcept, Coding, Identifier


def test_serialize_coding_should_suceed() -> None:
    expected = {"system": "some-system", "code": "some-code", "display": "some-display"}
    data = Coding(system="some-system", code="some-code", display="some-display")

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_coding_should_succeed() -> None:
    expected = Coding(system="some-system", code="some-code", display="some-display")
    data = {"system": "some-system", "code": "some-code", "display": "some-display"}

    actual = Coding.model_validate(data)

    assert expected == actual


def test_serialize_codeable_concept_should_succeed() -> None:
    expected = {"coding": [{"system": "some-system", "code": "some-code", "display": "some-display"}]}
    data = CodeableConcept(coding=[Coding(system="some-system", code="some-code", display="some-display")])

    actual = data.model_dump(exclude_none=True)

    assert expected == actual


def test_deserialize_codeable_concept_should_succeed() -> None:
    expected = CodeableConcept(coding=[Coding(system="some-system", code="some-code")])
    data = {"coding": [{"system": "some-system", "code": "some-code"}]}

    actual = CodeableConcept.model_validate(data)

    assert expected == actual


def test_serialize_identifier_should_succeed() -> None:
    expected = {"system": "some-system", "value": "some-value"}
    data = Identifier(system="some-system", value="some-value")

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_identifier_should_succeed() -> None:
    expected = Identifier(system="some-system", value="some-value")
    data = {"system": "some-system", "value": "some-value"}

    actual = Identifier.model_validate(data)

    assert expected == actual


def test_coding_from_query_bare_code_uses_default_system() -> None:
    actual = Coding.from_query("some-code", system="some-system")
    assert actual == Coding(system="some-system", code="some-code")


def test_coding_from_query_system_and_code() -> None:
    actual = Coding.from_query("some-system|some-code", system="some-system")
    assert actual == Coding(system="some-system", code="some-code")


def test_coding_from_query_absent_system() -> None:
    actual = Coding.from_query("|some-code", system="some-system")
    assert actual == Coding(system="", code="some-code")


def test_coding_from_query_system_only_any_code() -> None:
    actual = Coding.from_query("some-system|", system="some-system")
    assert actual == Coding(system="some-system", code="")


def test_coding_from_query_unknown_system_raises() -> None:
    with pytest.raises(ValueError, match="Unrecognized system"):
        Coding.from_query("other-system|some-code", system="some-system")


def test_coding_from_query_multiple_pipes_raises() -> None:
    with pytest.raises(ValueError, match="Invalid query format"):
        Coding.from_query("a|b|c", system="some-system")


def test_identifier_from_query_bare_value_uses_default_system() -> None:
    actual = Identifier.from_query("some-value", system="some-system")
    assert actual == Identifier(system="some-system", value="some-value")


def test_identifier_from_query_system_and_value() -> None:
    actual = Identifier.from_query("some-system|some-value", system="some-system")
    assert actual == Identifier(system="some-system", value="some-value")


def test_identifier_from_query_absent_system() -> None:
    actual = Identifier.from_query("|some-value", system="some-system")
    assert actual == Identifier(system="", value="some-value")


def test_identifier_from_query_system_only_any_value() -> None:
    actual = Identifier.from_query("some-system|", system="some-system")
    assert actual == Identifier(system="some-system", value="")


def test_identifier_from_query_unknown_system_raises() -> None:
    with pytest.raises(ValueError, match="Unrecognized system"):
        Identifier.from_query("other-system|some-value", system="some-system")


def test_identifier_from_query_multiple_pipes_raises() -> None:
    with pytest.raises(ValueError, match="Invalid query format"):
        Identifier.from_query("a|b|c", system="some-system")
