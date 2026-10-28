from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.key_info import KeyInfoEntity
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository


def test_find_by_id_should_succeed(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_by_id(mock_referral_entity.id)

        assert mock_referral_entity == actual


def test_find_by_id_should_return_none_when_no_match_found(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        some_id = uuid4()
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_by_id(some_id)

        assert actual is None


def test_find_many_should_return_one_item(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)
        expected = [mock_referral_entity]

        actual = referral_repository.find_many(
            pseudonym=mock_referral_entity.pseudonym,
            ura_number=mock_referral_entity.ura_number,
        )

    assert expected == actual


def test_find_many_should_return_two_item(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    mock_referral_entity_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        source="Some-Device2",
        key_info=mock_key_info,
    )
    mock_referral_entity.key_info = mock_key_info
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        referral_repository.add_one(mock_referral_entity_2)
        expected = [mock_referral_entity, mock_referral_entity_2]

        actual = referral_repository.find_many(
            pseudonym=mock_referral_entity.pseudonym,
            ura_number=mock_referral_entity.ura_number,
        )

    assert expected == actual


def test_find_many_with_alternative_params_should_succeed(
    referral_repository: ReferralRepository, mock_key_info: KeyInfoEntity
) -> None:
    mock_referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        source="Some-Device",
        key_info=mock_key_info,
    )
    mock_referral_2 = ReferralEntity(
        ura_number="0000124",
        pseudonym="ps-2",
        source="Some-Other-Device",
        key_info=mock_key_info,
    )
    expected = [mock_referral_1, mock_referral_2]

    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_1)
        referral_repository.add_one(mock_referral_2)
        actual = referral_repository.find_many()

    assert expected == actual


def _referrals_created_in_reverse_order(key_info: KeyInfoEntity, amount: int) -> list[ReferralEntity]:
    """Referrals that are inserted newest first, so the order of a query cannot follow the insertion order."""
    first = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        ReferralEntity(
            ura_number="0000123",
            pseudonym=f"ps-{i}",
            source="Some-Device",
            key_info=key_info,
            created_at=first + timedelta(minutes=i),
        )
        for i in reversed(range(amount))
    ]


def test_find_many_should_order_by_creation_time(
    referral_repository: ReferralRepository,
    mock_key_info: KeyInfoEntity,
) -> None:
    referrals = _referrals_created_in_reverse_order(mock_key_info, 3)

    with referral_repository.db_session:
        for referral in referrals:
            referral_repository.add_one(referral)
        actual = referral_repository.find_many(ura_number="0000123")

    assert [r.pseudonym for r in actual] == ["ps-0", "ps-1", "ps-2"]


def test_find_many_should_return_the_requested_page(
    referral_repository: ReferralRepository,
    mock_key_info: KeyInfoEntity,
) -> None:
    referrals = _referrals_created_in_reverse_order(mock_key_info, 5)

    with referral_repository.db_session:
        for referral in referrals:
            referral_repository.add_one(referral)
        first_page = referral_repository.find_many(ura_number="0000123", limit=2)
        second_page = referral_repository.find_many(ura_number="0000123", limit=2, offset=2)
        last_page = referral_repository.find_many(ura_number="0000123", limit=2, offset=4)

    assert [r.pseudonym for r in first_page] == ["ps-0", "ps-1"]
    assert [r.pseudonym for r in second_page] == ["ps-2", "ps-3"]
    assert [r.pseudonym for r in last_page] == ["ps-4"]


def test_count_should_apply_the_filters(
    referral_repository: ReferralRepository,
    mock_key_info: KeyInfoEntity,
) -> None:
    referrals = _referrals_created_in_reverse_order(mock_key_info, 3)
    other_ura = ReferralEntity(ura_number="0000124", pseudonym="ps-0", source="Some-Device", key_info=mock_key_info)

    with referral_repository.db_session:
        for referral in [*referrals, other_ura]:
            referral_repository.add_one(referral)

        assert referral_repository.count() == 4
        assert referral_repository.count(ura_number="0000123") == 3
        assert referral_repository.count(ura_number="0000123", pseudonym="ps-1") == 1
        assert referral_repository.count(source="Unknown-Device") == 0


def test_find_many_should_return_empty_list(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_many(
            pseudonym="differenet-pseudonym",
            ura_number=mock_referral_entity.ura_number,
        )

    assert actual == []


def test_add_one_should_succeed(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        actual = referral_repository.add_one(mock_referral_entity)

    assert mock_referral_entity == actual


def test_add_one_with_same_id_should_raise_exception(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        mock_referral_entity_2 = ReferralEntity(
            id=mock_referral_entity.id,
            pseudonym="some-other-pseudonym",
            ura_number=mock_referral_entity.ura_number,
            source=mock_referral_entity.source,
            key_id=mock_key_info.id,
        )

        referral_repository.add_one(mock_referral_entity)
        with pytest.raises(SQLAlchemyError) as exec:
            referral_repository.add_one(mock_referral_entity_2)

        assert isinstance(exec.value, IntegrityError)


def test_add_one_with_same_unique_index_should_raise_exception(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        mock_2 = ReferralEntity(
            ura_number=mock_referral_entity.ura_number,
            pseudonym=mock_referral_entity.pseudonym,
            source=mock_referral_entity.source,
            key_id=mock_key_info.id,
        )
        referral_repository.add_one(mock_referral_entity)
        with pytest.raises(SQLAlchemyError) as exec:
            referral_repository.add_one(mock_2)

        assert isinstance(exec.value, IntegrityError)


def test_delete_one_should_succeed(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)
        assert (
            referral_repository.exists(
                pseudonym=mock_referral_entity.pseudonym,
                ura_number=mock_referral_entity.ura_number,
            )
            is True
        )

        referral_repository.delete_one(mock_referral_entity)

        assert (
            referral_repository.exists(
                pseudonym=mock_referral_entity.pseudonym,
                ura_number=mock_referral_entity.ura_number,
            )
            is False
        )


def test_delete_one_should_raise_exception_when_does_not_exist(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session, pytest.raises(SQLAlchemyError):
        referral_repository.delete_one(mock_referral_entity)


def test_delete_with_only_ura_number_should_remove_all_recordss(
    referral_repository: ReferralRepository, mock_key_info: KeyInfoEntity
) -> None:
    referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        source="SomeDevice",
        key_info=mock_key_info,
    )
    referral_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-2",
        source="SomeOtherDevice",
        key_info=mock_key_info,
    )
    # referral from a different provider
    referral_3 = ReferralEntity(
        ura_number="0000125",
        pseudonym="ps-3",
        source="AntoherDevice",
        key_info=mock_key_info,
    )
    with referral_repository.db_session:
        referral_repository.add_one(referral_1)
        referral_repository.add_one(referral_2)
        referral_repository.add_one(referral_3)

        referral_repository.delete(ura_number="0000123")

        assert referral_repository.exists(ura_number="0000123") is False
        assert referral_repository.exists(ura_number="0000125") is True


def test_delete_with_pseudonym_should_remove_all_records_for_patient(
    referral_repository: ReferralRepository, mock_key_info: KeyInfoEntity
) -> None:
    referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        source="ImagingMachine",
        key_info=mock_key_info,
    )
    referral_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        source="SomeEPD",
        key_info=mock_key_info,
    )
    # referral from a different patient
    referral_3 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-2",
        source="SomeXRay",
        key_info=mock_key_info,
    )
    with referral_repository.db_session:
        referral_repository.add_one(referral_1)
        referral_repository.add_one(referral_2)
        referral_repository.add_one(referral_3)

        referral_repository.delete(ura_number="0000123", pseudonym="ps-1")

        assert referral_repository.exists(ura_number="0000123", pseudonym="ps-1") is False
        # not all records from this ura are gone
        assert referral_repository.exists(ura_number="0000123") is True
        # patient ps-2 still exists
        assert referral_repository.exists(ura_number="0000123", pseudonym="ps-2") is True


def test_delete_should_raise_exception_when_connection_to_db_is_down(
    referral_repository: ReferralRepository,
) -> None:
    db = Database(
        config_database=ConfigDatabase(
            dsn=SecretStr("postgresql+psycopg://postgres:connection@does_not_exists:12345/imaginary-db"),
            retry_backoff=[0.1, 0.2, 0.4],
        )
    )
    referral_repository.db_session = db.get_db_session()
    with referral_repository.db_session, pytest.raises(SQLAlchemyError):
        referral_repository.delete(ura_number="123")


def test_exists_should_return_true_if_record_is_there(
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_key_info: KeyInfoEntity,
) -> None:
    with referral_repository.db_session:
        mock_referral_entity.key_info = mock_key_info
        referral_repository.add_one(mock_referral_entity)

        exist = referral_repository.exists(
            pseudonym=mock_referral_entity.pseudonym,
            ura_number=mock_referral_entity.ura_number,
        )

        assert exist is True


def test_exists_should_return_false_if_record_is_not_there(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        exist = referral_repository.exists(
            pseudonym=mock_referral_entity.pseudonym,
            ura_number=mock_referral_entity.ura_number,
        )

        assert exist is False
