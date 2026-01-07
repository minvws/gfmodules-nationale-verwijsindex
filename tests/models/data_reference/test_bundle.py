from datetime import datetime
from uuid import uuid4

from app.models.data_reference.bundle import Bundle, BundleEntry
from app.models.data_reference.resource import (
    CARE_CONTEXT_SYSTEM,
    SOURCE_SYSTEM,
    SOURCE_TYPE_SYSTEM,
    CodeableConcept,
    Coding,
    Identifier,
    NVIDataReferenceBaseId,
    NVIDataReferenceOutput,
)


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
                    "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
                    "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
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
                    source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
                    source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
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
                    "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
                    "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
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
                resource=NVIDataReferenceBaseId(
                    id=resource_id,
                    source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
                    source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
                    care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
                )
            )
        ],
    )

    actual = Bundle.model_validate(data)

    assert expected == actual


def test_from_reference_output_should_succeed() -> None:
    output = NVIDataReferenceOutput(
        id=uuid4(),
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    expected = Bundle(total=1, entry=[BundleEntry(resource=output)])

    actual = Bundle.from_reference_outputs([output])

    assert expected == actual
