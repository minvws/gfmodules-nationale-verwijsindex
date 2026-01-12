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

    actual = data.model_dump()

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
