from typing import Any, Dict

import pytest

from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.pseudonym import Pseudonym
from app.models.referrals.entry import ReferralEntry
from app.models.ura import UraNumber


def test_serialize_should_succeed() -> None:
    expected = {
        "pseudonym": "encrypted data",
        "data_domain": "ImagingStudy",
        "ura_number": "00000123",
        "organization_type": "Hospital",
    }
    data = ReferralEntry(
        pseudonym=Pseudonym("encrypted data"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=UraNumber("123"),
        organization_type="Hospital",
    )

    actual = data.model_dump()

    assert expected == actual


def test_deserialize_should_succeed() -> None:
    data = {
        "pseudonym": "data",
        "data_domain": "ImagingStudy",
        "ura_number": 123,
    }
    expected = ReferralEntry(
        pseudonym=Pseudonym("data"),
        data_domain=DataDomain("ImagingStudy"),
        ura_number=UraNumber("123"),
    )

    actual = ReferralEntry.model_validate(data)

    assert expected == actual
    assert isinstance(actual.data_domain, DataDomain)
    assert isinstance(actual.ura_number, UraNumber)
    assert isinstance(actual.pseudonym, Pseudonym)


@pytest.mark.parametrize(
    "data",
    [
        {
            "pseudonym": "value",
            "data_domain": "value",
            "ura_number": "abc123",
        },
        {
            "pseudonym": "value",
            "data_domain": "value",
            "ura_number": 123456789010,
        },
    ],
)
def test_deserialize_should_raise_value_error_with_wrong_values(
    data: Dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        ReferralEntry.model_validate(data)


def test_from_entity_should_succeed() -> None:
    data = ReferralEntity(
        ura_number="00000123",
        pseudonym="some-pseudonym",
        data_domain="ImagingStudy",
    )
    expected = ReferralEntry(
        ura_number=UraNumber("123"),
        pseudonym=Pseudonym("some-pseudonym"),
        data_domain=DataDomain("ImagingStudy"),
    )

    actual = ReferralEntry.from_entity(data)

    assert expected == actual
