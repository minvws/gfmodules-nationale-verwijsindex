from uuid import uuid4

import pytest

from app.db.models.referral import ReferralEntity
from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.data import (
    CARE_CONTEXT_SYSTEM,
    ORG_SYSTEM,
    ORG_TYPE_SYSTEM,
    SOURCE_SYSTEM,
    SUBJECT_SYSTEM,
)
from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
    NVIDataRefrenceInput,
)


def test_serialize_nvi_data_reference_input_should_succeed() -> None:
    data = NVIDataRefrenceInput(
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
        subject=Identifier(system=SUBJECT_SYSTEM, value="some-jwe"),
        oprf_key="some-key",
    )
    expected = {
        "resourceType": "NVIDataReference",
        "organization": {"system": ORG_SYSTEM, "value": "00000123"},
        "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    actual = data.model_dump(by_alias=True, exclude_none=True)

    assert expected == actual


def test_deserialize_nvi_data_reference_input_should_succeed() -> None:
    expected = NVIDataRefrenceInput(
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        subject=Identifier(system=SUBJECT_SYSTEM, value="some-jwe"),
        oprf_key="some-key",
    )
    data = {
        "organization": {"system": ORG_SYSTEM, "value": "00000123"},
        "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    actual = NVIDataRefrenceInput.model_validate(data)

    assert expected == actual


def test_serialize_nvi_data_reference_output_should_succeed() -> None:
    resource_id = uuid4()
    data = NVIDataReferenceOutput(
        id=resource_id,
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    expected = {
        "id": resource_id,
        "resourceType": "NVIDataReference",
        "organization": {"system": ORG_SYSTEM, "value": "00000123"},
        "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    actual = data.model_dump(by_alias=True, exclude_none=True)

    assert expected == actual


def test_deserialize_nvi_data_reference_output_should_succeed() -> None:
    resource_id = uuid4()
    expected = NVIDataReferenceOutput(
        id=resource_id,
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis")]),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    data = {
        "id": resource_id,
        "organization": {"system": ORG_SYSTEM, "value": "00000123"},
        "organizationType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    actual = NVIDataReferenceOutput.model_validate(data)

    assert expected == actual


def test_create_nvi_data_reference_input_shoulf_fail_when_source_is_abscent() -> None:
    data = {
        "id": uuid4(),
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_with_incorrect_source() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": "WRONG SOURCE", "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_source_is_not_identifier() -> None:
    data = {
        "id": uuid4(),
        "source": {"WRONG_PROPETY": "some-value"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_organization_type_is_abscent() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_organization_type_is_not_codeable_concept() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"WRONG_PROPETY": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_more_than_one_value_in_organization_type() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "sourceType": {
            "coding": [
                {"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"},
                {"system": ORG_TYPE_SYSTEM, "code": "Pharmacy"},
            ]
        },
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_organization_type_has_wrong_system() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": "WRONG SYSTEM", "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_care_context_is_abscent() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_care_context_is_not_codeable_concept() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"WRONG_PROPETY": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_care_context_has_more_than_one_coding() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {
            "coding": [
                {"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"},
                {"system": CARE_CONTEXT_SYSTEM, "code": "MedicationStatment"},
            ]
        },
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_care_context_has_wrong_system() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": "WRONG SYSTEM", "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_is_abscent() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_is_not_identifier() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"WRONG_PROPERTY": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_has_wrong_system() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": "WRONG SYSTEM", "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_with_invalid_ura_number() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "INVALID_URA_NUMBER_WITH_CHARS"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "ziekenhuis"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_nvi_data_reference_output_from_entity_should_fail_with_invalid_organization_type_value() -> None:
    referral = ReferralEntity(
        id=uuid4(),
        ura_number="00000123",
        organization_type="INVALID_ORGANIZATION_TYPE",
        data_domain="ImagingStudy",
        pseudonym="some-pseudonym",
    )

    with pytest.raises(ValueError):
        NVIDataReferenceOutput.from_referral(referral)


def test_nvi_data_reference_input_from_entity_should_fail_with_invalid_organization_type_value() -> None:
    data = {
        "id": uuid4(),
        "source": {"system": SOURCE_SYSTEM, "value": "SomeDevice"},
        "sourceType": {"coding": [{"system": ORG_TYPE_SYSTEM, "code": "INVALID_ORGANIZATION_TYPE"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_from_entity_should_succeed() -> None:
    resource_id = uuid4()
    expected = NVIDataReferenceOutput(
        id=resource_id,
        organization=Identifier(system=ORG_SYSTEM, value="00000123"),
        organization_type=CodeableConcept(
            coding=[Coding(system=ORG_TYPE_SYSTEM, code="ziekenhuis", display="Ziekenhuis")]
        ),
        source=Identifier(system=SOURCE_SYSTEM, value="SomeDevice"),
        care_context=CodeableConcept(
            coding=[
                Coding(
                    system=CARE_CONTEXT_SYSTEM,
                    code="ImagingStudy",
                    display="Beeldvormend onderzoek",
                )
            ]
        ),
    )
    referral = ReferralEntity(
        id=resource_id,
        ura_number="00000123",
        organization_type="ziekenhuis",
        data_domain="ImagingStudy",
        source="SomeDevice",
        pseudonym="some-pseudonym",
    )

    actual = NVIDataReferenceOutput.from_referral(referral)

    assert expected == actual
