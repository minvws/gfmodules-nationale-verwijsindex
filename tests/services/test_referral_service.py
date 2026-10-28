import logging
from typing import Any
from uuid import UUID, uuid4

import pytest
from gfmodules.logging import LogEvent

from app.db.models.referral import ReferralEntity
from app.logging.events import Log
from app.models.pseudonym import EncryptedPseudonym
from app.models.ura import UraNumber
from app.services.exceptions import (
    NotFoundError,
)
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService

REQUESTING_URA = UraNumber("00000456")
PSEUDONYM = EncryptedPseudonym("ps-1", "123")
SOURCE = "SomeDevice"


def logged_fields(caplog: pytest.LogCaptureFixture, event: LogEvent) -> list[dict[str, Any]]:
    return [vars(record) for record in caplog.records if getattr(record, "event_id", None) == event.event_id]


def store_referral(
    referral_service: ReferralService, key_info_service: KeyInfoService, ura_number: UraNumber
) -> ReferralEntity:
    key_info = key_info_service.add_one("label-1", "AES_CBC")
    referral, _ = referral_service.add_one(
        encrypted_pseudonym=PSEUDONYM,
        ura_number=ura_number,
        source=SOURCE,
        key_id=key_info.id,
    )
    return referral


def assert_eq(
    expected: ReferralEntity | list[ReferralEntity],
    actual: ReferralEntity | list[ReferralEntity],
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
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info = key_info_service.add_one("some-label", "AES_CBC")
    expected, _ = referral_service.add_one(
        encrypted_pseudonym=EncryptedPseudonym("ps-1", "123"),
        ura_number=ura_number,
        source="SomeDevice",
        key_id=key_info.id,
    )
    assert isinstance(expected.id, UUID)
    actual = referral_service.get_by_id(expected.id)

    assert_eq(expected, actual)


def test_add_referral_is_idempotent_for_duplicates(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info = key_info_service.add_one("label-1", "AES_CBC")
    patient = EncryptedPseudonym("ps-1", "123")
    first, first_created = referral_service.add_one(
        encrypted_pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
        key_id=key_info.id,
    )

    second, second_created = referral_service.add_one(
        encrypted_pseudonym=patient,
        ura_number=ura_number,
        source="SomeDevice",
        key_id=key_info.id,
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert len(referral_service.get_many(ura_number=ura_number)) == 1


def test_read_returns_the_callers_referral_and_logs_the_search(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    with caplog.at_level(logging.INFO):
        actual = referral_service.read(referral.id, ura_number)

    (fields,) = logged_fields(caplog, Log.REFERRAL_SEARCHED_ON_ID)
    assert_eq(referral, actual)
    assert fields["pseudonym_hash"] == str(PSEUDONYM)


def test_read_hides_another_uras_referral_behind_not_found(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    with caplog.at_level(logging.INFO), pytest.raises(NotFoundError):
        referral_service.read(referral.id, REQUESTING_URA)

    (denied,) = logged_fields(caplog, Log.REFERRAL_ACCESS_DENIED)
    assert denied["resource_ura"] == str(ura_number)
    assert logged_fields(caplog, Log.REFERRAL_SEARCHED_ON_ID) == []


def test_read_raises_not_found_for_an_unknown_id(referral_service: ReferralService, ura_number: UraNumber) -> None:
    with pytest.raises(NotFoundError):
        referral_service.read(uuid4(), ura_number)


def test_delete_by_id_should_succeed(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    referral_service.delete_by_id(referral.id, ura_number, SOURCE)

    with pytest.raises(NotFoundError) as exec:
        referral_service.get_by_id(referral.id)

    assert "Record not found" in str(exec.value)


def test_delete_by_id_logs_the_deleted_referral(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    with caplog.at_level(logging.INFO):
        referral_service.delete_by_id(referral.id, ura_number, SOURCE)

    (fields,) = logged_fields(caplog, Log.REFERRAL_DELETED)
    assert fields["pseudonym_hash"] == str(PSEUDONYM)


def test_delete_by_id_hides_another_uras_referral_behind_not_found(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    with caplog.at_level(logging.INFO), pytest.raises(NotFoundError):
        referral_service.delete_by_id(referral.id, REQUESTING_URA, SOURCE)

    assert len(logged_fields(caplog, Log.REFERRAL_ACCESS_DENIED)) == 1
    assert logged_fields(caplog, Log.REFERRAL_DELETED) == []
    assert referral_service.get_by_id(referral.id).id == referral.id


def test_delete_by_id_hides_another_sources_referral_behind_not_found(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    referral = store_referral(referral_service, key_info_service, ura_number)
    assert isinstance(referral.id, UUID)

    with caplog.at_level(logging.INFO), pytest.raises(NotFoundError):
        referral_service.delete_by_id(referral.id, ura_number, "OtherDevice")

    assert logged_fields(caplog, Log.REFERRAL_DELETED) == []
    assert referral_service.get_by_id(referral.id).id == referral.id


def test_delet_by_id_should_raise_exception_when_no_match_found(
    referral_service: ReferralService,
    ura_number: UraNumber,
) -> None:
    some_id = uuid4()
    with pytest.raises(NotFoundError) as exec:
        referral_service.delete_by_id(some_id, ura_number, SOURCE)

    assert "Record not found" in str(exec.value)


def test_delete_many_with_a_pseudonym_logs_patient_scope(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store_referral(referral_service, key_info_service, ura_number)

    with caplog.at_level(logging.INFO):
        deleted = referral_service.delete_many(ura_number, encrypted_pseudonym=PSEUDONYM, source=SOURCE)

    (fields,) = logged_fields(caplog, Log.ALL_PATIENT_REFERRALS_DELETED)
    assert deleted == 1
    assert fields["pseudonym_hash"] == str(PSEUDONYM)
    assert fields["deleted_count"] == 1


def test_delete_many_without_a_pseudonym_logs_ura_scope(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store_referral(referral_service, key_info_service, ura_number)

    with caplog.at_level(logging.INFO):
        referral_service.delete_many(ura_number, source=SOURCE)

    (fields,) = logged_fields(caplog, Log.ALL_URA_REFERRALS_DELETED)
    assert fields["deleted_count"] == 1


def test_delete_many_logs_nothing_when_nothing_matched(
    referral_service: ReferralService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        deleted = referral_service.delete_many(ura_number, encrypted_pseudonym=PSEUDONYM)

    assert deleted == 0
    assert logged_fields(caplog, Log.ALL_PATIENT_REFERRALS_DELETED) == []
    assert logged_fields(caplog, Log.ALL_URA_REFERRALS_DELETED) == []


def test_localize_logs_success_with_the_pseudonym_and_result_count(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store_referral(referral_service, key_info_service, ura_number)

    with caplog.at_level(logging.INFO):
        referrals = referral_service.localize(PSEUDONYM, REQUESTING_URA)

    (fields,) = logged_fields(caplog, Log.LOCALIZATION_SUCCESS)
    assert len(referrals) == 1
    assert fields["pseudonym_hash"] == str(PSEUDONYM)
    assert fields["result_count"] == 1


def test_localize_logs_no_match_with_a_zero_result_count(
    referral_service: ReferralService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        referrals = referral_service.localize(PSEUDONYM, REQUESTING_URA)

    (fields,) = logged_fields(caplog, Log.LOCALIZATION_NO_MATCH)
    assert len(referrals) == 0
    assert fields["result_count"] == 0


def test_localize_does_not_log_a_query(
    referral_service: ReferralService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert logged_fields(caplog, Log.REFERRALS_QUERIED) == []


def test_query_logs_the_result_count(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store_referral(referral_service, key_info_service, ura_number)

    with caplog.at_level(logging.INFO):
        referrals = referral_service.query(ura_number, encrypted_pseudonym=PSEUDONYM)

    (fields,) = logged_fields(caplog, Log.REFERRALS_QUERIED)
    assert len(referrals) == 1
    assert fields["result_count"] == 1


def test_query_is_scoped_to_the_callers_ura(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    store_referral(referral_service, key_info_service, ura_number)

    assert len(referral_service.query(REQUESTING_URA, encrypted_pseudonym=PSEUDONYM)) == 0
