from datetime import datetime
from uuid import uuid4

from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.data import (
    CARE_CONTEXT_SYSTEM,
    ORG_SYSTEM,
    ORG_TYPE_SYSTEM,
    SOURCE_SYSTEM,
)
from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)
from app.models.fhir.resources.organization.resource import Organization


def test_serialize_should_succeed() -> None:
    timestamp = datetime.now()
    resource_id = uuid4()
    expected = {
        "resourceType": "Bundle",
        "type": "searchset",
        "timestamp": timestamp,
        "total": 1,
        "entry": [
            {
                "resource": {
                    "id": resource_id,
                    "resourceType": "NVIDataReference",
                    "organization": {"system": ORG_SYSTEM, "value": "00000123"},
                    "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
                    "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
                    "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
                }
            }
        ],
    }

    data = Bundle(
        timestamp=timestamp,
        total=1,
        entry=[
            BundleEntry(
                resource=NVIDataReferenceOutput(
                    id=resource_id,
                    organization=Identifier(system=ORG_SYSTEM, value="00000123"),
                    source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
                    organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
                    care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
                )
            )
        ],
    )

    actual = data.model_dump(exclude_none=True, by_alias=True)

    assert expected == actual


def test_deserialize_should_succeed() -> None:
    timestamp = datetime.now()
    resource_id = uuid4()
    data = {
        "resourceType": "Bundle",
        "type": "searchset",
        "timestamp": timestamp,
        "total": 1,
        "entry": [
            {
                "resource": {
                    "id": resource_id,
                    "organization": {"system": ORG_SYSTEM, "value": "00000123"},
                    "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
                    "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
                    "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
                }
            }
        ],
    }
    expected = Bundle(
        timestamp=timestamp,
        total=1,
        entry=[
            BundleEntry(
                resource=NVIDataReferenceOutput(
                    id=resource_id,
                    organization=Identifier(system=ORG_SYSTEM, value="00000123"),
                    organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
                    source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
                    care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
                )
            )
        ],
    )

    actual = Bundle[NVIDataReferenceOutput].model_validate(data)

    assert expected == actual


def test_from_reference_output_should_succeed() -> None:
    bundle_id = uuid4()
    output = NVIDataReferenceOutput(
        id=uuid4(),
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    expected = Bundle(total=1, entry=[BundleEntry(resource=output)], id=str(bundle_id))

    actual = Bundle.from_reference_outputs([output], bundle_id)

    assert expected == actual


def test_from_organizations_should_succeed(mock_org: Organization) -> None:
    bundle_id = uuid4()
    expected = Bundle(total=1, entry=[BundleEntry(resource=mock_org)], id=str(bundle_id))

    actual = Bundle.from_organizations([mock_org], bundle_id)

    assert expected == actual
