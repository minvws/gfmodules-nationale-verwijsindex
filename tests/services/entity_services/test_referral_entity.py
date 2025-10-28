import pytest
from fastapi import HTTPException

from app.data import DataDomain, Pseudonym, UraNumber
from app.data_models.referrals import ReferralEntry
from app.db.models.referral import ReferralEntity
from app.services.entity.referral_entity_service import ReferralEntityService


@pytest.fixture()
def mock_referral() -> ReferralEntry:
    return ReferralEntry(
        ura_number=UraNumber("12345"),
        pseudonym=Pseudonym(value="6d87d96a-cb78-4f5c-823b-578095da2c4a"),
        data_domain=DataDomain(value="ImagingStudy"),
        encrypted_lmr_id="encrypted_lmr_id_12345",
        lmr_endpoint="https://example.com",
    )


@pytest.fixture()
def mock_referral_2() -> ReferralEntry:
    return ReferralEntry(
        ura_number=UraNumber("54321"),
        pseudonym=Pseudonym(value="8d4882ec-824e-4cd1-bc66-5b47d3d8eaaf"),
        data_domain=DataDomain(value="MedicationStatement"),
        encrypted_lmr_id="encrypted_lmr_id_54321",
        lmr_endpoint="https://example.com",
    )


def _helper_add_referral(
    referral_entity_service: ReferralEntityService,
    mock_referral: ReferralEntry,
) -> ReferralEntry:
    return referral_entity_service.add_one_referral(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
        encrypted_lmr_id=mock_referral.encrypted_lmr_id,
        lmr_endpoint=mock_referral.lmr_endpoint,
    )


def test_add_one_referral_succeeds(
    mock_referral: ReferralEntry, referral_entity_service: ReferralEntityService
) -> None:
    added_referral = _helper_add_referral(referral_entity_service, mock_referral)
    assert added_referral == mock_referral


def test_add_duplicate_referral_raises_http_exception(
    mock_referral: ReferralEntry,
    referral_entity_service: ReferralEntityService,
) -> None:
    _helper_add_referral(referral_entity_service, mock_referral)
    with pytest.raises(HTTPException) as exc_info:
        _helper_add_referral(referral_entity_service, mock_referral)
    assert exc_info.value.status_code == 409


def test_delete_one_referral_succeeds(
    mock_referral: ReferralEntry,
    referral_entity_service: ReferralEntityService,
) -> None:
    _helper_add_referral(referral_entity_service, mock_referral)
    referral_entity_service.delete_one_referral(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
    )
    with pytest.raises(HTTPException) as exc_info:
        referral_entity_service.query_referrals()
    assert exc_info.value.status_code == 404


def test_delete_nonexistent_referral_raises_http_exception(
    mock_referral: ReferralEntry,
    referral_entity_service: ReferralEntityService,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        referral_entity_service.delete_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
    assert exc_info.value.status_code == 404


def test_query_referrals(
    mock_referral: ReferralEntry,
    mock_referral_2: ReferralEntry,
    referral_entity_service: ReferralEntityService,
) -> None:
    _helper_add_referral(referral_entity_service, mock_referral)
    _helper_add_referral(referral_entity_service, mock_referral_2)

    results = referral_entity_service.query_referrals(
        pseudonym=mock_referral.pseudonym,
        data_domain=mock_referral.data_domain,
        ura_number=mock_referral.ura_number,
    )
    assert len(results) == 1
    assert results[0] == mock_referral

    results = referral_entity_service.query_referrals(
        pseudonym=mock_referral.pseudonym,
    )
    assert len(results) == 1
    assert results[0] == mock_referral

    results = referral_entity_service.query_referrals(
        data_domain=mock_referral_2.data_domain,
    )
    assert len(results) == 1
    assert results[0] == mock_referral_2

    results = referral_entity_service.query_referrals()
    assert len(results) == 2


def test_query_no_matching_referrals_raises_http_exception(
    referral_entity_service: ReferralEntityService,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        referral_entity_service.query_referrals(
            pseudonym=Pseudonym(value="nonexistent-pseudonym"),
        )
    assert exc_info.value.status_code == 404


def test_hydrate_referral(
    mock_referral: ReferralEntry,
    referral_entity_service: ReferralEntityService,
) -> None:
    entity = ReferralEntity(**mock_referral.model_dump())
    assert referral_entity_service.hydrate_referral(entity) == mock_referral
