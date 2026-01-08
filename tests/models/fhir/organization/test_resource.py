from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.organization.resource import Organization


def test_serialize_organization_should_succeed() -> None:
    expected = {
        "resourceType": "Organization",
        "id": "123456789",
        "identifier": [{"system": "some-system", "value": "some-value"}],
        "active": True,
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
        "name": "some-name",
    }
    data = Organization(
        id="123456789",
        identifier=[Identifier(system="some-system", value="some-value")],
        active=True,
        type=[CodeableConcept(coding=[Coding(system="some-system", code="some-code", display="some-display")])],
        name="some-name",
    )

    actual = data.model_dump(by_alias=True)

    assert expected == actual


def test_deserialize_should_succeed() -> None:
    data = {
        "resourceType": "Organization",
        "id": "123456789",
        "identifier": [{"system": "some-system", "value": "some-value"}],
        "active": True,
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
        "name": "some-name",
    }
    expected = Organization(
        id="123456789",
        identifier=[Identifier(system="some-system", value="some-value")],
        active=True,
        type=[CodeableConcept(coding=[Coding(system="some-system", code="some-code", display="some-display")])],
        name="some-name",
    )

    actual = Organization.model_validate(data)

    assert expected == actual
