from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.referral_service import ReferralService


def test_add_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    expected = referral_service.add_one(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )
    assert isinstance(expected.id, UUID)
    actual = referral_service.get_by_id(expected.id)

    assert expected == actual


def test_add_referral_should_raise_exception_with_duplicates(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")
    org_type = "ziekenhuis"
    referral_service.add_one(
        pseudonym=patient,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type=org_type,
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.add_one(
            pseudonym=patient,
            data_domain=data_domain,
            ura_number=ura_number,
            organization_type=org_type,
        )

    assert exec.value.status_code == 409


def test_delete_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("MedicationAgreement")
    data = referral_service.add_one(
        pseudonym=patient,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type="huisarts",
    )
    assert isinstance(data.id, UUID)
    nvi_reference = referral_service.get_by_id(data.id)
    assert data == nvi_reference
    referral_service.delete_one(
        pseudonym=patient,
        data_domain=data_domain,
        ura_number=ura_number,
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.get_by_id(data.id)

    assert exec.value.status_code == 404


def test_delete_one_should_raise_exception_when_not_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")

    with pytest.raises(HTTPException) as exec:
        referral_service.delete_one(
            pseudonym=patient,
            data_domain=data_domain,
            ura_number=ura_number,
        )

    assert exec.value.status_code == 404


def test_get_registration_with_specific_patient_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    localisation_pseudonym = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")

    data = referral_service.add_one(
        pseudonym=localisation_pseudonym,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )

    referral_service.add_one(
        pseudonym=Pseudonym("ps-2"),
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )

    expected = [data]

    actual = referral_service.get_registrations(
        ura_number=data.get_ura_number(),
        pseudonym=localisation_pseudonym,
        data_domain=data.get_data_domain(),
    )

    assert expected == actual


def test_get_registrations_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    patient_1 = Pseudonym("ps-1")
    patient_2 = Pseudonym("ps-2")
    data_domain_1 = DataDomain("ImagingStudy")
    data_domain_2 = DataDomain("MedicationAgreement")
    org_type = "ziekenhuis"

    expected_1 = referral_service.add_one(
        pseudonym=patient_1,
        data_domain=data_domain_1,
        ura_number=ura_number,
        organization_type=org_type,
    )
    expected_2 = referral_service.add_one(
        pseudonym=patient_2,
        data_domain=data_domain_2,
        ura_number=ura_number,
        organization_type=org_type,
    )
    expected = [expected_1, expected_2]
    actual = referral_service.get_registrations(ura_number=ura_number)

    assert expected == actual


def test_delete_patient_registrations_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    patient_1 = Pseudonym("ps-1")
    referral_service.add_one(
        pseudonym=patient_1,
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )
    referral_service.add_one(
        pseudonym=patient_1,
        data_domain=DataDomain("MedicationAgreement"),
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )

    patient_2 = Pseudonym("ps-2")
    patient_2_reference_1 = referral_service.add_one(
        pseudonym=patient_2,
        data_domain=DataDomain("MedicationAgreement"),
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )

    expected = [patient_2_reference_1]

    referral_service.delete_patient_registrations(ura_number=ura_number, pseudonym=patient_1)

    actual = referral_service.get_registrations(ura_number)

    assert expected == actual


def test_delete_patient_registrations_should_raise_exception_when_not_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    with pytest.raises(FHIRException) as exec:
        referral_service.delete_patient_registrations(ura_number=ura_number, pseudonym=Pseudonym("ps-1"))

    assert exec.value.status_code == 404


def test_delete_specific_registration_should_suceed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("MedicationAgreement")
    org_type = "umc"
    referral_service.add_one(
        pseudonym=patient,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type=org_type,
    )

    referral_service.delete_specific_registration(
        ura_number=ura_number,
        data_domain=data_domain,
        pseudonym=patient,
    )
    actual = referral_service.get_registrations(
        ura_number=ura_number,
        data_domain=data_domain,
        pseudonym=patient,
    )

    assert actual == []


def test_delete_specific_registration_should_raise_exception_when_no_match_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("MedicationAgreement")
    with pytest.raises(HTTPException) as exec:
        referral_service.delete_specific_registration(
            ura_number=ura_number,
            data_domain=data_domain,
            pseudonym=patient,
        )

    assert exec.value.status_code == 404


def test_delete_organizaton_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    ura_a = ura_number
    ura_a_type = "ziekenhuis"
    patient_1 = Pseudonym("ps-1")
    patient_1_data_domain = DataDomain("ImagingStudy")
    patient_1_referecne = referral_service.add_one(
        pseudonym=patient_1,
        data_domain=patient_1_data_domain,
        ura_number=ura_a,
        organization_type=ura_a_type,
    )
    patient_2 = Pseudonym("ps-2")
    patient_2_data_domain = DataDomain("MedicationAgreement")
    patient_2_reference = referral_service.add_one(
        pseudonym=patient_2,
        data_domain=patient_2_data_domain,
        ura_number=ura_a,
        organization_type=ura_a_type,
    )
    assert referral_service.get_registrations(ura_number=ura_a) == [
        patient_1_referecne,
        patient_2_reference,
    ]

    ura_b = UraNumber("98765432")
    patient_3 = Pseudonym("ps-3")
    patient_3_data_domain = DataDomain("MedicationAgreement")
    ura_b_type = "ziekenhuis"
    patient_3_reference = referral_service.add_one(
        pseudonym=patient_3,
        data_domain=patient_3_data_domain,
        ura_number=ura_b,
        organization_type=ura_b_type,
    )

    referral_service.delete_specific_organization(ura_number=ura_a)
    actual_org_1 = referral_service.get_registrations(ura_number=ura_a)
    actual_org_2 = referral_service.get_registrations(ura_number=ura_b)

    assert actual_org_1 == []
    assert actual_org_2 == [patient_3_reference]


def test_delete_specific_organization_should_raise_exception_when_no_match_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    with pytest.raises(FHIRException) as exec:
        referral_service.delete_specific_organization(ura_number)

    assert exec.value.status_code == 404


def test_delete_by_id_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    patient = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")
    patient_reference = referral_service.add_one(
        pseudonym=patient,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )
    assert isinstance(patient_reference.id, UUID)
    referral_service.delete_by_id(patient_reference.id)
    with pytest.raises(FHIRException) as exec:
        referral_service.get_by_id(patient_reference.id)

    assert exec.value.status_code == 404


def test_delet_by_id_should_raise_exception_when_no_match_found(
    referral_service: ReferralService,
) -> None:
    some_id = uuid4()
    with pytest.raises(FHIRException) as exec:
        referral_service.delete_by_id(some_id)

    assert exec.value.status_code == 404


def test_get_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    pseudonym = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")

    expected = referral_service.add_one(
        pseudonym=pseudonym,
        data_domain=data_domain,
        ura_number=ura_number,
        organization_type="ziekenhuis",
    )

    actual = referral_service.get_one(
        pseudonym=pseudonym,
        data_domain=data_domain,
        ura_number=ura_number,
    )

    assert actual is not None
    assert expected == actual


def test_get_one_should_return_none_when_not_found(referral_service: ReferralService, ura_number: UraNumber) -> None:
    pseudonym = Pseudonym("ps-1")
    data_domain = DataDomain("ImagingStudy")
    actual = referral_service.get_one(
        pseudonym=pseudonym,
        data_domain=data_domain,
        ura_number=ura_number,
    )

    assert actual is None
