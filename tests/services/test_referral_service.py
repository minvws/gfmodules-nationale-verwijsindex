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
        encrypted_lmr_id="encrypted_lmr_id_12345",
        lmr_endpoint="https://example.com",
        organization_type="Hospital",
    )


def test_add_one_should_succeed(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    actual = referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        encrypted_lmr_id=mock_referral.encrypted_lmr_id,
        lmr_endpoint=mock_referral.lmr_endpoint,
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
        encrypted_lmr_id=mock_referral.encrypted_lmr_id,
        lmr_endpoint=mock_referral.lmr_endpoint,
        uzi_number="12345678",
        request_url="http://example.com",
        organization_type=mock_referral.organization_type,
    )
    with pytest.raises(HTTPException) as exec:
        referral_service.add_one(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            encrypted_lmr_id=mock_referral.encrypted_lmr_id,
            lmr_endpoint=mock_referral.lmr_endpoint,
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
        encrypted_lmr_id=mock_referral.encrypted_lmr_id,
        lmr_endpoint=mock_referral.lmr_endpoint,
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


def test_delete_referral_should_succeed(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    data = referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        encrypted_lmr_id=mock_referral.encrypted_lmr_id,
        lmr_endpoint=mock_referral.lmr_endpoint,
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


def test_delete_referral_should_raise_exception_when_not_found(
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


def test_query_referral_single_item(referral_service: ReferralService, mock_referral: ReferralEntry) -> None:
    referral_service.add_one(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        uzi_number="testuzinumber",
        request_url="https://test",
        lmr_endpoint="https://example.com",
        encrypted_lmr_id="encrypted_lmr_id_12345",
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
        encrypted_lmr_id="encrypted_lmr_id_12345",
        lmr_endpoint="https://example.com",
    )

    referral_service.add_one(
        pseudonym=Pseudonym("some other pseudonym"),
        data_domain=DataDomain("MedicationStatement"),
        ura_number=ura_number,
        uzi_number="testuzi_number",
        request_url="http://example.com",
        lmr_endpoint="https://example.com",
        encrypted_lmr_id="encrypted_lmr_id_12345",
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
