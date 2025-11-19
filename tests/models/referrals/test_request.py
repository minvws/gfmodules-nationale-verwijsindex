from typing import Dict

import pytest

from app.models.data_domain import DataDomain
from app.models.referrals.requests import (
    CreateReferralRequest,
    ReferralQuery,
)
from app.models.ura import UraNumber


def test_deserialize_create_referral_request_should_succed() -> None:
    expected = {
        "oprf_jwe": "jwe",
        "blind_factor": "factor",
        "data_domain": "domain",
        "ura_number": "00000123",
        "requesting_uzi_number": "123456",
        "encrypted_lmr_id": "some-id",
        "lmr_endpoint": "http://example.com",
    }

    data = CreateReferralRequest(
        oprf_jwe="jwe",
        blind_factor="factor",
        data_domain=DataDomain("domain"),
        ura_number=UraNumber("123"),
        requesting_uzi_number="123456",
        encrypted_lmr_id="some-id",
        lmr_endpoint="http://example.com",
    )

    actual = data.model_dump()

    assert expected == actual


def test_serialize_create_referral_request_should_succeed() -> None:
    expected = CreateReferralRequest(
        oprf_jwe="jwe",
        blind_factor="factor",
        data_domain=DataDomain("domain"),
        ura_number=UraNumber("123"),
        requesting_uzi_number="123456",
        encrypted_lmr_id="some-id",
        lmr_endpoint="http://example.com",
    )
    data = {
        "oprf_jwe": "jwe",
        "blind_factor": "factor",
        "data_domain": "domain",
        "ura_number": "00000123",
        "requesting_uzi_number": "123456",
        "encrypted_lmr_id": "some-id",
        "lmr_endpoint": "http://example.com",
    }

    actual = CreateReferralRequest.model_validate(data)

    assert expected == actual


@pytest.mark.parametrize(
    "data",
    [
        {
            "oprf_jwe": "jwe",
            "blind_factor": "factor",
            "data_domain": "domain",
            "ura_number": "abcd",
            "requesting_uzi_number": "123456",
            "encrypted_lmr_id": "some-id",
            "lmr_endpoint": "http://example.com",
        },
        {
            "oprf_jwe": "jwe",
            "blind_factor": "factor",
            "data_domain": "domain",
            "ura_number": "00000000000123",
            "requesting_uzi_number": "123456",
            "encrypted_lmr_id": "some-id",
            "lmr_endpoint": "http://example.com",
        },
    ],
)
def test_create_referral_request_should_raise_value_error(
    data: Dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        CreateReferralRequest.model_validate(data)


def test_serialize_referral_query_should_succeed() -> None:
    data = ReferralQuery(
        oprf_jwe="jwe",
        blind_factor="factor",
        data_domain=DataDomain("domain"),
        ura_number=UraNumber(123),
    )
    expected = {
        "oprf_jwe": "jwe",
        "blind_factor": "factor",
        "data_domain": "domain",
        "ura_number": "00000123",
    }

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_referral_query_should_succeeds() -> None:
    data = {
        "oprf_jwe": "jwe",
        "blind_factor": "factor",
        "data_domain": "domain",
        "ura_number": "00000123",
    }
    expected = ReferralQuery(
        oprf_jwe="jwe",
        blind_factor="factor",
        data_domain=DataDomain("domain"),
        ura_number=UraNumber(123),
    )

    actual = ReferralQuery.model_validate(data)

    assert expected == actual


@pytest.mark.parametrize(
    "data",
    [
        {
            # missing oprf
            "blind_factor": "factor",
            "data_domain": "domain",
            "ura_number": "00000123",
        },
        {
            # missing blind_factor
            "oprf_jwe": "oprf",
            "data_domain": "domain",
            "ura_number": "00000123",
        },
        {
            # invalid ura number
            "oprf_jwe": "jwe",
            "blind_factor": "factor",
            "ura_number": "abc123",
        },
    ],
)
def test_deserialize_referral_query_should_raise_value_error(
    data: Dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        ReferralQuery.model_validate(data)
