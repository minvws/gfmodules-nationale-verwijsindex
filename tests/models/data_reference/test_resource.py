import pytest

from app.db.models.referral import ReferralEntity
from app.models.data_reference.resource import (
    CARE_CONTEXT_SYSTEM,
    SOURCE_SYSTEM,
    SOURCE_TYPE_SYSTEM,
    SUBJECT_SYSTEM,
    CodeableConcept,
    Coding,
    Identifier,
    NVIDataReferenceOutput,
    NVIDataRefrenceInput,
)


def test_serialize_coding_should_suceed() -> None:
    expected = {"system": "some-system", "code": "some-code"}
    data = Coding(system="some-system", code="some-code")

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_coding_should_succeed() -> None:
    expected = Coding(system="some-system", code="some-code")
    data = {"system": "some-system", "code": "some-code"}

    actual = Coding.model_validate(data)

    assert expected == actual


def test_serialize_codeable_concept_should_succeed() -> None:
    expected = {"coding": [{"system": "some-system", "code": "some-code"}]}
    data = CodeableConcept(coding=[Coding(system="some-system", code="some-code")])

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


def test_serialize_nvi_data_reference_input_should_succeed() -> None:
    data = NVIDataRefrenceInput(
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
        subject=Identifier(system=SUBJECT_SYSTEM, value="some-jwe"),
        oprf_key="some-key",
    )
    expected = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    actual = data.model_dump(by_alias=True)

    assert expected == actual


def test_deserialize_nvi_data_reference_input_should_succeed() -> None:
    expected = NVIDataRefrenceInput(
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
        subject=Identifier(system=SUBJECT_SYSTEM, value="some-jwe"),
        oprf_key="some-key",
    )
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    actual = NVIDataRefrenceInput.model_validate(data)

    assert expected == actual


def test_serialize_nvi_data_reference_output_should_succeed() -> None:
    data = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    expected = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    actual = data.model_dump(by_alias=True)

    assert expected == actual


def test_deserialize_nvi_data_reference_output_should_succeed() -> None:
    expected = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    actual = NVIDataReferenceOutput.model_validate(data)

    assert expected == actual


def test_create_nvi_data_reference_input_shoulf_fail_when_source_is_abscent() -> None:
    data = {
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_with_incorrect_source() -> None:
    data = {
        "source": {"system": "WRONG SOURCE", "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_source_is_not_identifier() -> None:
    data = {
        "source": {"WRONG_PROPETY": "some-value"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_source_type_is_abscent() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_source_type_is_not_codeable_concept() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"WRONG_PROPETY": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_more_than_one_value_in_source_type() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {
            "coding": [
                {"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"},
                {"system": SOURCE_TYPE_SYSTEM, "code": "Pharmacy"},
            ]
        },
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_source_type_has_wrong_system() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": "WRONG SYSTEM", "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_care_context_is_abscent() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_care_context_is_not_codeable_concept() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"WRONG_PROPETY": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_should_fail_when_care_context_has_more_than_one_coding() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
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
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": "WRONG SYSTEM", "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }

    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_is_abscent() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_is_not_identifier() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"WRONG_PROPERTY": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_when_subject_has_wrong_system() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "00000123"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": "WRONG SYSTEM", "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_create_nvi_data_reference_input_should_fail_with_invalid_ura_number() -> None:
    data = {
        "source": {"system": SOURCE_SYSTEM, "value": "INVALID_URA_NUMBER_WITH_CHARS"},
        "sourceType": {"coding": [{"system": SOURCE_TYPE_SYSTEM, "code": "Hospital"}]},
        "careContext": {"coding": [{"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"}]},
        "subject": {"system": SUBJECT_SYSTEM, "value": "some-jwe"},
        "oprfKey": "some-key",
    }
    with pytest.raises(ValueError):
        NVIDataRefrenceInput.model_validate(data)


def test_from_entity_should_succeed() -> None:
    expected = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value="00000123"),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    referral = ReferralEntity(
        ura_number="00000123",
        organization_type="Hospital",
        data_domain="ImagingStudy",
        pseudonym="some-pseudonym",
    )

    actual = NVIDataReferenceOutput.from_referral(referral)

    assert expected == actual
