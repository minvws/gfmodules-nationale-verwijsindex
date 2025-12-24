import pytest
from fastapi import HTTPException

from app.models.data_domain import DataDomain
from app.models.data_reference.resource import (
    CARE_CONTEXT_SYSTEM,
    SOURCE_SYSTEM,
    SOURCE_TYPE_SYSTEM,
    CodeableConcept,
    Coding,
    Identifier,
    NVIDataReferenceOutput,
)
from app.models.pseudonym import Pseudonym
from app.models.referrals.entry import ReferralEntry
from app.models.ura import UraNumber
from app.services.referral_service import ReferralService


@pytest.fixture()
def mock_referral() -> ReferralEntry:
    return ReferralEntry(
        ura_number=UraNumber("123"),
        pseudonym=Pseudonym(value="6d87d96a-cb78-4f5c-823b-578095da2c4a"),
        data_domain=DataDomain(value="ImagingStudy"),
        organization_type="Hospital",
    )


@pytest.fixture()
def mock_nvi_reference_data(ura_number: UraNumber) -> NVIDataReferenceOutput:
    return NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )


def test_add_one_should_succeed(
    referral_service: ReferralService, mock_nvi_reference_data: NVIDataReferenceOutput
) -> None:
    actual = referral_service.add_one(
        pseudonym=Pseudonym("ps-1"),
        data_domain=mock_nvi_reference_data.get_data_domain(),
        ura_number=mock_nvi_reference_data.get_ura_number(),
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_nvi_reference_data.get_organization_type(),
    )

    assert mock_nvi_reference_data == actual


def test_add_referral_should_raise_exception_with_duplicates(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.add_one(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            uzi_number="12345678",
            request_url="http://example.com",
            organization_type=mock_referral.organization_type,
        )

    assert exec.value.status_code == 409


def test_get_referral_by_domain_and_pseudonym_should_succeed(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )

    actual = referral_service.get_referrals_by_domain_and_pseudonym(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
    )[0]

    assert mock_referral == actual


def test_get_referral_by_domain_and_pseudonym_should_raise_exception_when_not_found(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
        )

    assert exec.value.status_code == 404


def test_delete_one_should_succeed(
    referral_service: ReferralService, mock_nvi_reference_data: NVIDataReferenceOutput
) -> None:
    patient = Pseudonym("ps-1")
    data = referral_service.add_one(
        pseudonym=patient,
        data_domain=mock_nvi_reference_data.get_data_domain(),
        ura_number=mock_nvi_reference_data.get_ura_number(),
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_nvi_reference_data.get_organization_type(),
    )
    assert data == mock_nvi_reference_data
    referral_service.delete_one(
        pseudonym=patient,
        data_domain=mock_nvi_reference_data.get_data_domain(),
        ura_number=mock_nvi_reference_data.get_ura_number(),
        request_url="http://example.com",
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=patient,
            data_domain=mock_nvi_reference_data.get_data_domain(),
        )

    assert exec.value.status_code == 404


def test_delete_one_should_raise_exception_when_not_found(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.delete_one(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            request_url="http://example.com",
        )

    assert exec.value.status_code == 404


def test_get_specific_patient_should_succeed(
    referral_service: ReferralService, mock_nvi_reference_data: NVIDataReferenceOutput
) -> None:
    localisation_pseudonym = Pseudonym("ps-1")
    referral_service.add_one(
        pseudonym=localisation_pseudonym,
        data_domain=mock_nvi_reference_data.get_data_domain(),
        ura_number=mock_nvi_reference_data.get_ura_number(),
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_nvi_reference_data.get_organization_type(),
    )

    expected = [mock_nvi_reference_data]

    actual = referral_service.get_specific_patient(
        ura_number=UraNumber(mock_nvi_reference_data.source.value),
        pseudonym=localisation_pseudonym,
        data_domain=DataDomain(mock_nvi_reference_data.care_context.coding[0].code),
    )

    assert expected == actual


def test_get_specific_patient_should_return_empty_list_when_no_match_found(
    referral_service: ReferralService,
) -> None:
    actual = referral_service.get_specific_patient(
        ura_number=UraNumber("123"),
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
    )

    assert actual == []


def test_get_all_registrations_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    nvi_reference_1 = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    nvi_reference_2 = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="MedicationStatement")]),
    )
    expected = [nvi_reference_1, nvi_reference_2]

    referral_service.add_one(
        pseudonym=Pseudonym("ps-1"),
        data_domain=nvi_reference_1.get_data_domain(),
        ura_number=ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=nvi_reference_1.get_organization_type(),
    )
    referral_service.add_one(
        pseudonym=Pseudonym("ps-2"),
        data_domain=nvi_reference_2.get_data_domain(),
        ura_number=ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=nvi_reference_2.get_organization_type(),
    )
    actual = referral_service.get_all_registrations(ura_number=ura_number)

    assert expected == actual


def test_delete_patient_registrations_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    pseudonym_1 = Pseudonym("ps-1")
    ps1_reference_1 = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    ps1_reference_2 = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="MedicationStatement")]),
    )

    pseudonym_2 = Pseudonym("ps-2")
    ps2_reference = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_number)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="Medication")]),
    )
    referral_3 = ReferralEntry(
        pseudonym=Pseudonym("ps-2"),
        data_domain=DataDomain("MedicationStatment"),
        ura_number=ura_number,
        organization_type="Hospital",
    )
    referral_service.add_one(
        pseudonym=pseudonym_1,
        data_domain=ps1_reference_1.get_data_domain(),
        ura_number=ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
    )
    referral_service.add_one(
        pseudonym=pseudonym_1,
        data_domain=ps1_reference_2.get_data_domain(),
        ura_number=ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
    )

    referral_service.add_one(
        pseudonym=pseudonym_2,
        data_domain=ps2_reference.get_data_domain(),
        ura_number=ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=referral_3.organization_type,
    )

    expected = [ps2_reference]

    referral_service.delete_patient_registrations(ura_number=ura_number, pseudonym=pseudonym_1)

    actual = referral_service.get_all_registrations(ura_number)

    assert expected == actual


def test_delete_patient_registrations_should_raise_exception_when_not_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.delete_patient_registrations(ura_number=ura_number, pseudonym=Pseudonym("ps-1"))

    assert exec.value.status_code == 404


def test_delete_specific_registration_should_suceed(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )

    referral_service.delete_specific_registration(
        ura_number=mock_referral.ura_number,
        data_domain=mock_referral.data_domain,
        pseudonym=mock_referral.pseudonym,
    )
    actual = referral_service.get_specific_patient(
        ura_number=mock_referral.ura_number,
        data_domain=mock_referral.data_domain,
        pseudonym=mock_referral.pseudonym,
    )

    assert actual == []


def test_delete_specific_registration_should_raise_exception_when_no_match_found(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.delete_specific_registration(
            ura_number=mock_referral.ura_number,
            data_domain=mock_referral.data_domain,
            pseudonym=mock_referral.pseudonym,
        )

    assert exec.value.status_code == 404


def test_delete_organizaton_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    ura_a = ura_number
    patient_1 = Pseudonym("ps-1")
    patient_1_ref = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_a)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy")]),
    )
    patient_2 = Pseudonym("ps-2")
    patient_2_ref = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_a)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Hospital")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="Medication")]),
    )
    ura_b = UraNumber("98765432")
    patient_3 = Pseudonym("ps-3")
    patient_3_ref = NVIDataReferenceOutput(
        source=Identifier(system=SOURCE_SYSTEM, value=str(ura_b)),
        source_type=CodeableConcept(coding=[Coding(system=SOURCE_TYPE_SYSTEM, code="Pharmacy")]),
        care_context=CodeableConcept(coding=[Coding(system=CARE_CONTEXT_SYSTEM, code="Medication")]),
    )
    referral_service.add_one(
        pseudonym=patient_1,
        data_domain=patient_1_ref.get_data_domain(),
        ura_number=ura_a,
        uzi_number="123456",
        request_url="http://example.com",
        organization_type=patient_3_ref.get_organization_type(),
    )
    referral_service.add_one(
        pseudonym=patient_2,
        data_domain=patient_2_ref.get_data_domain(),
        ura_number=ura_a,
        uzi_number="123456",
        request_url="http://example.com",
        organization_type=patient_3_ref.get_organization_type(),
    )
    referral_service.add_one(
        pseudonym=patient_3,
        data_domain=patient_3_ref.get_data_domain(),
        ura_number=ura_b,
        uzi_number="123456",
        request_url="http://example.com",
        organization_type=patient_3_ref.get_organization_type(),
    )

    referral_service.delete_specific_organization(ura_number=ura_a)
    actual_org_1 = referral_service.get_all_registrations(ura_number=ura_a)
    actual_org_2 = referral_service.get_all_registrations(ura_number=ura_b)

    assert actual_org_1 == []
    assert actual_org_2 == [patient_3_ref]


def test_delete_specific_organization_should_raise_exception_when_no_match_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.delete_specific_organization(ura_number)

    assert exec.value.status_code == 404


def test_query_referral_single_item(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="testuzinumber",
        request_url="https://test",
        organization_type=mock_referral.organization_type,
    )

    actual_referrals = referral_service.query_referrals(
        pseudonym=mock_referral.pseudonym,
        ura_number=mock_referral.ura_number,
        data_domain=None,
        request_url="http://test",
    )

    for r in actual_referrals:
        assert r == mock_referral


def test_query_referral_two_items(referral_service: ReferralService, ura_number: UraNumber) -> None:
    referral_service.add_one(
        uzi_number="testuzi_number",
        pseudonym=Pseudonym("some-pseudonym"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
        request_url="http://example.com",
    )

    referral_service.add_one(
        pseudonym=Pseudonym("some other pseudonym"),
        data_domain=DataDomain("MedicationStatement"),
        ura_number=ura_number,
        uzi_number="testuzi_number",
        request_url="http://example.com",
    )

    actual_referrals = referral_service.query_referrals(
        pseudonym=None,
        ura_number=ura_number,
        data_domain=None,
        request_url="http://example.com",
    )

    assert len(actual_referrals) == 2


def test_query_referral_should_raise_exception_when_not_found(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    with pytest.raises(HTTPException) as exec:
        referral_service.query_referrals(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            request_url="http://example.com",
        )

    assert exec.value.status_code == 404
