from datetime import datetime
from uuid import UUID, uuid4

from app.models.fhir.bundle import Bundle, BundleEntry, EntryRequestDto
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


class TestEntryRequestDtoFromUrl:
    def test_parses_resource_and_id(self) -> None:
        dto = EntryRequestDto.from_url("List/0f14d0ab-9605-4a62-a9e4-5ed26688389b")

        assert dto.resource == "List"
        assert dto.id == UUID("0f14d0ab-9605-4a62-a9e4-5ed26688389b")
        assert dto.params is None

    def test_keeps_a_single_query_parameter(self) -> None:
        # A one-criterion search is the common case; dropping it made the entry parse
        # as a paramless query and fail validation.
        dto = EntryRequestDto.from_url("List?source:identifier=SRC-001")

        assert dto.params == {"source:identifier": "SRC-001"}

    def test_keeps_multiple_query_parameters(self) -> None:
        dto = EntryRequestDto.from_url("List?source:identifier=SRC-001&subject:identifier=pseu")

        assert dto.params == {"source:identifier": "SRC-001", "subject:identifier": "pseu"}

    def test_has_no_params_when_query_is_absent(self) -> None:
        assert EntryRequestDto.from_url("List").params is None
