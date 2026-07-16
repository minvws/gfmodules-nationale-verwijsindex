import datetime

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.models.key_info import KeyInfoEntity
from app.db.repository.key_info_repository import KeyInfoRepository


def test_find_one_should_succeed(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        key_info_repository.add_one(mock_key_info)
        actual = key_info_repository.find_one(mock_key_info.label)

    for c in mock_key_info.__table__.columns:
        expected_attr = getattr(mock_key_info, c.name)
        actual_attr = getattr(actual, c.name)

        assert expected_attr == actual_attr


def test_find_should_return_none_with_no_data(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        expected = key_info_repository.find_one(mock_key_info.label)

    assert expected is None


def test_find_should_return_none_with_soft_delete(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        mock_key_info.deleted_at = datetime.datetime.now()
        data = key_info_repository.add_one(mock_key_info)

        actual = key_info_repository.find_one(mock_key_info.label)

    assert data is not None
    assert actual is None


def test_find_should_return_none_for_incative_keys(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        mock_key_info.active = False
        data = key_info_repository.add_one(mock_key_info)

        actual = key_info_repository.find_one(mock_key_info.label)

    assert data is not None
    assert actual is None


def test_add_one_succeeds(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        expected = key_info_repository.add_one(mock_key_info)
        actual = key_info_repository.find_one(expected.label)

    assert expected == actual


def test_add_one_should_raise_on_duplicates(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    mock_2 = KeyInfoEntity(label=mock_key_info.label, mechanism="AES_GCM")
    with key_info_repository.db_session:
        key_info_repository.add_one(mock_key_info)

        with pytest.raises(SQLAlchemyError) as exc:
            key_info_repository.add_one(mock_2)

    assert isinstance(exc.value, IntegrityError)


def test_find_many_should_return_two(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        key_info_repository.add_one(mock_key_info)
        key_info_repository.add_one(KeyInfoEntity(label="label-2", mechanism=mock_key_info.mechanism))

        results = key_info_repository.find_many(mock_key_info.mechanism)

    assert len(results) == 2


def test_find_many_should_return_empty_list(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        actual = key_info_repository.find_many(mock_key_info.label)

    assert len(actual) == 0


def test_find_many_should_ignore_soft_deleted_keys(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        mock_2 = KeyInfoEntity(
            label="label-2",
            mechanism=mock_key_info.mechanism,
            deleted_at=datetime.datetime.now(),
        )

        key_info_repository.add_one(mock_key_info)
        key_info_repository.add_one(mock_2)

        actual = key_info_repository.find_many(mock_key_info.mechanism)

    assert len(actual) == 1
    assert actual[0] == mock_key_info


def test_find_active_should_ignore_inactive_keys(
    key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity
) -> None:
    with key_info_repository.db_session:
        mock_2 = KeyInfoEntity(label="label-2", mechanism=mock_key_info.mechanism, active=False)

        key_info_repository.add_one(mock_key_info)
        key_info_repository.add_one(mock_2)

        actual = key_info_repository.find_active()

    assert len(actual) == 1
    assert actual[0] == mock_key_info


def test_exists_should_true_with_label(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        key_info_repository.add_one(mock_key_info)

        actual = key_info_repository.exists(mock_key_info.label)

    assert actual is True


def test_exists_should_true_with_id(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        data = key_info_repository.add_one(mock_key_info)

        actual = key_info_repository.exists(id=data.id)

    assert actual is True


def test_exists_should_return_false(key_info_repository: KeyInfoRepository, mock_key_info: KeyInfoEntity) -> None:
    with key_info_repository.db_session:
        key_info_repository.add_one(mock_key_info)

        actual = key_info_repository.exists("some-other-label")

    assert actual is False
