import pytest

from app.data_models.referrals import (
    CreateReferralRequest,
    DeleteReferralRequest,
    ReferralEntry,
    ReferralQuery,
    ReferralRequest,
)
from app.data_models.typing import DataDomain, Pseudonym, UraNumber
from app.services.referral_service import ReferralService


@pytest.fixture()
def mock_referral() -> ReferralEntry:
    return ReferralEntry(
        ura_number=UraNumber(12345),
        pseudonym=Pseudonym(value="6d87d96a-cb78-4f5c-823b-578095da2c4a"),
        data_domain=DataDomain(value="ImagingStudy"),
        encrypted_lmr_id="encrypted_lmr_id_12345",
    )


@pytest.fixture()
def create_req(
    mock_referral: ReferralEntry,
) -> CreateReferralRequest:
    return CreateReferralRequest(
        requesting_uzi_number="test_uzi_number",
        ura_number=mock_referral.ura_number,
        data_domain=mock_referral.data_domain,
        encrypted_lmr_id="encrypted_lmr_id_12345",
        oprf_jwe="test_oprf_jwe",
        blind_factor="test_blind_factor",
    )


@pytest.fixture()
def query_request(
    mock_referral: ReferralEntry,
) -> ReferralQuery:
    return ReferralQuery(
        requesting_uzi_number="test_uzi_number",
        ura_number=mock_referral.ura_number,
        oprf_jwe="test_oprf_jwe",
        blind_factor="test_blind_factor",
        data_domain=DataDomain(value="ImagingStudy"),
    )


@pytest.fixture()
def referral_request() -> ReferralRequest:
    return ReferralRequest(
        oprf_jwe="test_oprf_jwe",
        blind_factor="test_blind_factor",
        data_domain=DataDomain(value="ImagingStudy"),
    )


def test_create_referral_succeeds(
    mock_referral: ReferralEntry,
    referral_service: ReferralService,
    create_req: CreateReferralRequest,
) -> None:
    referral_service._prs_service.exchange.return_value = mock_referral.pseudonym  # type: ignore

    _entry = referral_service.create_referral(
        create_req=create_req,
        requesting_ura_number=UraNumber("1234"),
        request_url="https://example.com/create_referral",
    )

    referral_service._entity_service.add_one_referral.assert_called_once()  # type: ignore
    referral_service._audit_logger.log.assert_called_once()  # type: ignore


def test_create_referral_prs_fails(
    referral_service: ReferralService,
    create_req: CreateReferralRequest,
) -> None:
    referral_service._prs_service.exchange.side_effect = Exception("PRS error")  # type: ignore
    with pytest.raises(Exception) as excinfo:
        referral_service.create_referral(
            create_req=create_req,
            requesting_ura_number=UraNumber("1234"),
            request_url="https://example.com/create_referral",
        )
    assert "PRS error" in str(excinfo.value)


def test_query_referrals_succeeds(
    query_request: ReferralQuery,
    referral_service: ReferralService,
) -> None:
    _entries = referral_service.query_referrals(
        query_request=query_request,
        requesting_ura_number=UraNumber("1234"),
        request_url="https://example.com/query_referrals",
    )

    referral_service._prs_service.exchange.assert_called_once()  # type: ignore
    referral_service._entity_service.query_referrals.assert_called_once()  # type: ignore
    referral_service._audit_logger.log.assert_called_once()  # type: ignore


def test_query_referrals_prs_fails(
    referral_service: ReferralService,
    query_request: ReferralQuery,
) -> None:
    referral_service._prs_service.exchange.side_effect = Exception("PRS error")  # type: ignore

    with pytest.raises(Exception) as excinfo:
        referral_service.query_referrals(
            query_request=query_request,
            requesting_ura_number=UraNumber("1234"),
            request_url="https://example.com/query_referrals",
        )
    assert "PRS error" in str(excinfo.value)


def test_delete_referral_succeeds(
    mock_referral: ReferralEntry,
    referral_service: ReferralService,
    create_req: DeleteReferralRequest,
) -> None:
    referral_service._prs_service.exchange.return_value = mock_referral.pseudonym  # type: ignore

    referral_service.delete_referral(
        delete_request=create_req,
        requesting_ura_number=UraNumber("1234"),
        request_url="https://example.com/delete_referral",
    )

    referral_service._entity_service.delete_one_referral.assert_called_once()  # type: ignore
    referral_service._audit_logger.log.assert_called_once()  # type: ignore


def test_delete_referral_prs_fails(
    referral_service: ReferralService,
    create_req: DeleteReferralRequest,
) -> None:
    referral_service._prs_service.exchange.side_effect = Exception("PRS error")  # type: ignore

    with pytest.raises(Exception) as excinfo:
        referral_service.delete_referral(
            delete_request=create_req,
            requesting_ura_number=UraNumber("1234"),
            request_url="https://example.com/delete_referral",
        )
    assert "PRS error" in str(excinfo.value)


def test_request_uras_for_timeline_succeeds(
    referral_service: ReferralService, referral_request: ReferralRequest
) -> None:
    _ura_numbers = referral_service.request_uras_for_timeline(
        referral_request=referral_request,
        requesting_ura_number=UraNumber("1234"),
        requesting_uzi_number="test_uzi_number",
        request_url="https://example.com/",
        breaking_glass=True,
    )

    referral_service._prs_service.exchange.assert_called_once()  # type: ignore
    referral_service._entity_service.query_referrals.assert_called_once()  # type: ignore
    referral_service._audit_logger.log.assert_called_once()  # type: ignore
    referral_service._auth_service.is_authorized.assert_not_called()  # type: ignore
