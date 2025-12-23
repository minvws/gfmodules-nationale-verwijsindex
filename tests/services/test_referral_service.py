import pytest
from fastapi import HTTPException

from app.models.data_domain import DataDomain
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


def test_add_one_should_succeed(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    actual = referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )

    assert mock_referral == actual


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


def test_delete_one_should_succeed(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    data = referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )
    assert data == mock_referral
    referral_service.delete_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        request_url="http://example.com",
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
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


def test_get_specific_patient_should_succeed(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )

    expected = [mock_referral]

    actual = referral_service.get_specific_patient(
        ura_number=mock_referral.ura_number,
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
    )

    assert expected == actual


def test_get_specific_patient_should_return_empty_list_when_no_match_found(
    referral_service: ReferralService, mock_referral: ReferralEntry
) -> None:
    actual = referral_service.get_specific_patient(
        ura_number=UraNumber("123"),
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
    )

    assert actual == []


def test_get_all_registrations_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    referral_1 = ReferralEntry(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
    )
    referral_2 = ReferralEntry(
        pseudonym=Pseudonym("ps-2"),
        data_domain=DataDomain("MedicationStatment"),
        ura_number=ura_number,
        organization_type="Hospital",
    )
    expected = [referral_1, referral_2]

    referral_service.add_one(
        pseudonym=referral_1.pseudonym,
        data_domain=referral_1.data_domain,
        ura_number=referral_1.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
    )
    referral_service.add_one(
        pseudonym=referral_2.pseudonym,
        data_domain=referral_2.data_domain,
        ura_number=referral_2.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=referral_2.organization_type,
    )
    actual = referral_service.get_all_registrations(ura_number=ura_number)

    assert expected == actual


def test_delete_patient_registrations_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    referral_1 = ReferralEntry(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
    )
    referral_2 = ReferralEntry(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("Medication"),
        ura_number=ura_number,
    )
    referral_3 = ReferralEntry(
        pseudonym=Pseudonym("ps-2"),
        data_domain=DataDomain("MedicationStatment"),
        ura_number=ura_number,
        organization_type="Hospital",
    )
    referral_service.add_one(
        pseudonym=referral_1.pseudonym,
        data_domain=referral_1.data_domain,
        ura_number=referral_1.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
    )
    referral_service.add_one(
        pseudonym=referral_2.pseudonym,
        data_domain=referral_2.data_domain,
        ura_number=referral_2.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
    )

    referral_service.add_one(
        pseudonym=referral_3.pseudonym,
        data_domain=referral_3.data_domain,
        ura_number=referral_3.ura_number,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=referral_3.organization_type,
    )

    referral_service.delete_patient_registrations(ura_number=ura_number, pseudonym=Pseudonym("ps-1"))

    data = referral_service.get_all_registrations(
        ura_number=ura_number,
    )
    pseudonym_value_list = [e.pseudonym.value for e in data]
    assert referral_1.pseudonym.value not in pseudonym_value_list
    assert referral_2.pseudonym.value not in pseudonym_value_list
    assert referral_3.pseudonym.value in pseudonym_value_list


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
    referral_1 = ReferralEntry(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=ura_number,
    )
    referral_2 = ReferralEntry(
        pseudonym=Pseudonym("ps-1"),
        data_domain=DataDomain("Medication"),
        ura_number=ura_number,
    )
    referral_3 = ReferralEntry(
        pseudonym=Pseudonym("ps-2"),
        data_domain=DataDomain("MedicationStatment"),
        ura_number=UraNumber("456"),
    )
    referral_service.add_one(
        pseudonym=referral_1.pseudonym,
        data_domain=referral_1.data_domain,
        ura_number=referral_1.ura_number,
        uzi_number="123456",
        request_url="http://example.com",
    )
    referral_service.add_one(
        pseudonym=referral_2.pseudonym,
        data_domain=referral_2.data_domain,
        ura_number=referral_2.ura_number,
        uzi_number="123456",
        request_url="http://example.com",
    )
    referral_service.add_one(
        pseudonym=referral_3.pseudonym,
        data_domain=referral_3.data_domain,
        ura_number=referral_3.ura_number,
        uzi_number="123456",
        request_url="http://example.com",
    )

    referral_service.delete_specific_organization(ura_number=ura_number)
    actual_org_1 = referral_service.get_all_registrations(ura_number=ura_number)
    actual_org_2 = referral_service.get_all_registrations(ura_number=UraNumber("456"))

    assert actual_org_1 == []
    assert actual_org_2 == [referral_3]


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
