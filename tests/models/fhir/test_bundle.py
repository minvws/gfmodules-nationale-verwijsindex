from datetime import datetime
from uuid import uuid4

from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.elements import CodeableConcept, Coding, Identifier, Reference
from app.models.fhir.resources.data import (
    EMPTY_REASON_SYSTEM,
    URA_SYSTEM,
    URA_SYSTEM_EXTENSION,
)
from app.models.fhir.resources.localization_list.resource import (
    LocalizationList,
    ReferenceExtension,
)
from app.models.ura import UraNumber


def test_serialize_should_succeed(ura_number: UraNumber) -> None:
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
                    "resourceType": "List",
                    "id": resource_id,
                    "extension": [
                        {
                            "url": URA_SYSTEM_EXTENSION,
                            "valueReference": {
                                "identifier": {
                                    "value": ura_number.value,
                                    "system": URA_SYSTEM,
                                },
                            },
                        }
                    ],
                    "status": "current",
                    "mode": "working",
                    "source": {
                        "identifier": {
                            "system": "https://cp1-test.example.org/device-identifiers",
                            "value": "EHR-SYS-2024-001",
                        },
                        "type": "Device",
                    },
                    "emptyReason": {"coding": [{"system": EMPTY_REASON_SYSTEM, "code": "withheld"}]},
                }
            }
        ],
    }

    data = Bundle(
        timestamp=timestamp,
        total=1,
        entry=[
            BundleEntry(
                resource=LocalizationList(
                    id=resource_id,
                    extension=[
                        ReferenceExtension(
                            url=URA_SYSTEM_EXTENSION,
                            value_reference=Reference(identifier=Identifier(system=URA_SYSTEM, value=ura_number.value)),
                        )
                    ],
                    status="current",
                    mode="working",
                    source=Reference(
                        identifier=Identifier(
                            system="https://cp1-test.example.org/device-identifiers",
                            value="EHR-SYS-2024-001",
                        ),
                        type="Device",
                    ),
                    empty_reason=CodeableConcept(coding=[Coding(system=EMPTY_REASON_SYSTEM, code="withheld")]),
                )
            )
        ],
    )

    actual = data.model_dump(exclude_none=True, by_alias=True)

    assert expected == actual


def test_deserialize_should_succeed(ura_number: UraNumber) -> None:
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
                    "resourceType": "List",
                    "id": resource_id,
                    "extension": [
                        {
                            "url": URA_SYSTEM_EXTENSION,
                            "valueReference": {
                                "identifier": {
                                    "value": ura_number.value,
                                    "system": URA_SYSTEM,
                                },
                            },
                        }
                    ],
                    "status": "current",
                    "mode": "working",
                    "source": {
                        "identifier": {
                            "system": "https://cp1-test.example.org/device-identifiers",
                            "value": "EHR-SYS-2024-001",
                        },
                        "type": "Device",
                    },
                    "emptyReason": {"coding": [{"system": EMPTY_REASON_SYSTEM, "code": "withheld"}]},
                }
            }
        ],
    }

    expected = Bundle(
        timestamp=timestamp,
        total=1,
        entry=[
            BundleEntry(
                resource=LocalizationList(
                    id=resource_id,
                    extension=[
                        ReferenceExtension(
                            url=URA_SYSTEM_EXTENSION,
                            value_reference=Reference(identifier=Identifier(system=URA_SYSTEM, value=ura_number.value)),
                        )
                    ],
                    status="current",
                    mode="working",
                    source=Reference(
                        identifier=Identifier(
                            system="https://cp1-test.example.org/device-identifiers",
                            value="EHR-SYS-2024-001",
                        ),
                        type="Device",
                    ),
                    empty_reason=CodeableConcept(coding=[Coding(system=EMPTY_REASON_SYSTEM, code="withheld")]),
                )
            )
        ],
    )

    actual = Bundle[LocalizationList].model_validate(data)

    assert expected == actual
