from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.organization.resource import Organization


def test_serialize_organization_should_succeed() -> None:
    expected = {
        "resourceType": "Organization",
        "id": "123456789",
        "identifier": [{"system": "some-system", "value": "some-value"}],
        "type": [
            {
                "coding": [
                    {
                        "system": "some-system",
                        "code": "some-code",
                        "display": "some-display",
                    }
                ]
            }
        ],
    }
    data = Organization(
        id="123456789",
        identifier=[Identifier(system="some-system", value="some-value")],
        type=[CodeableConcept(coding=[Coding(system="some-system", code="some-code", display="some-display")])],
    )

    actual = data.model_dump(by_alias=True, exclude_none=True)

    assert expected == actual


def test_deserialize_should_succeed() -> None:
    data = {
        "resourceType": "Organization",
        "id": "123456789",
        "identifier": [{"system": "some-system", "value": "some-value"}],
        "type": [
            {
                "coding": [
                    {
                        "system": "some-system",
                        "code": "some-code",
                        "display": "some-display",
                    }
                ]
            }
        ],
    }
    expected = Organization(
        id="123456789",
        identifier=[Identifier(system="some-system", value="some-value")],
        type=[CodeableConcept(coding=[Coding(system="some-system", code="some-code", display="some-display")])],
    )

    actual = Organization.model_validate(data)

    assert expected == actual
