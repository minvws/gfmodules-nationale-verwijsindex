from typing import List
from uuid import UUID, uuid4

import pytest

from app.db.models.referral import ReferralEntity
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.exceptions import ConflictError, NotFoundError
from app.services.referral_service import ReferralService


def assert_eq(
    expected: ReferralEntity | List[ReferralEntity],
    actual: ReferralEntity | List[ReferralEntity],
) -> None:
    """
    Helper function to compare equality between objects.
    """

    def compare(expected: ReferralEntity, actual: ReferralEntity) -> None:
        expected_attr = expected.__table__.columns.keys()
        actual_attr = actual.__table__.columns.keys()

        assert expected_attr == actual_attr
        for attr in expected_attr:
            expected_value = getattr(expected, attr)
            actual_value = getattr(actual, attr)

            assert expected_value == actual_value

    match (expected, actual):
        case (ReferralEntity() as exp, ReferralEntity() as act):
            compare(exp, act)

        case (list() as exp, list() as act):
            assert len(exp) == len(act)
            for i, item in enumerate(exp):
                target = act[i]
                assert_eq(item, target)

        case _:
            raise TypeError("Cannot compare equality for obj of different types")


def test_add_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    expected = referral_service.add_one(
        pseudonym=Pseudonym("ps-1"),
        ura_number=ura_number,
        source="SomeDevice",
        organization_type="ziekenhuis",
    )
    assert isinstance(expected.id, UUID)
    actual = referral_service.get_by_id(expected.id)

    assert_eq(expected, actual)


def test_add_referral_should_raise_exception_with_duplicates(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    patient = Pseudonym("ps-1")
    org_type = "ziekenhuis"
    referral_service.add_one(
        pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
        organization_type=org_type,
    )
    with pytest.raises(ConflictError) as exec:
        referral_service.add_one(
            pseudonym=patient,
            ura_number=ura_number,
            source="SomeDevice",
            organization_type=org_type,
        )

    assert "Record already exists" in str(exec.value)


def test_delete_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    patient = Pseudonym("ps-1")
    data = referral_service.add_one(
        pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
        organization_type="huisarts",
    )
    assert isinstance(data.id, UUID)
    nvi_reference = referral_service.get_by_id(data.id)
    assert_eq(data, nvi_reference)
    referral_service.delete_one(
        pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
    )
    with pytest.raises(NotFoundError) as exec:
        referral_service.get_by_id(data.id)

    assert "Record not found" in str(exec.value)


def test_delete_one_should_raise_exception_when_not_found(
    referral_service: ReferralService, ura_number: UraNumber
) -> None:
    patient = Pseudonym("ps-1")

    with pytest.raises(NotFoundError) as exec:
        referral_service.delete_one(
            pseudonym=patient,
            source="SomeDevice",
            ura_number=ura_number,
        )

    assert "Record not found" in str(exec.value)


def test_delete_by_id_should_succeed(referral_service: ReferralService, ura_number: UraNumber) -> None:
    patient = Pseudonym("ps-1")
    patient_reference = referral_service.add_one(
        pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
        organization_type="ziekenhuis",
    )
    assert isinstance(patient_reference.id, UUID)
    referral_service.delete_by_id(patient_reference.id)
    with pytest.raises(NotFoundError) as exec:
        referral_service.get_by_id(patient_reference.id)

    assert "Record not found" in str(exec.value)


def test_delet_by_id_should_raise_exception_when_no_match_found(
    referral_service: ReferralService,
) -> None:
    some_id = uuid4()
    with pytest.raises(NotFoundError) as exec:
        referral_service.delete_by_id(some_id)

    assert "Record not found" in str(exec.value)


def test_get_one_should_succeed(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    pseudonym = Pseudonym("ps-1")

    expected = referral_service.add_one(
        pseudonym=pseudonym,
        ura_number=ura_number,
        source="SomeDevice",
        organization_type="ziekenhuis",
    )

    actual = referral_service.get_one(
        pseudonym=pseudonym,
        ura_number=ura_number,
        source="SomeDevice",
    )

    assert actual is not None
    assert_eq(expected, actual)


def test_get_one_should_return_none_when_not_found(referral_service: ReferralService, ura_number: UraNumber) -> None:
    pseudonym = Pseudonym("ps-1")
    actual = referral_service.get_one(
        pseudonym=pseudonym,
        ura_number=ura_number,
        source="SomeDevice",
    )

    assert actual is None
