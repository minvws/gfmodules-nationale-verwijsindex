from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import ConfigDatabase
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository


def test_find_by_id_should_succeed(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_by_id(mock_referral_entity.id)

        assert mock_referral_entity == actual


def test_find_by_id_should_return_none_when_no_match_found(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        some_id = uuid4()
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_by_id(some_id)

        assert actual is None


def test_find_many_should_return_one_item(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        expected = [mock_referral_entity]

        actual = referral_repository.find_many(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

    assert expected == actual


def test_find_many_should_return_two_item(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    mock_referral_entity_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        data_domain="MedicationStatement",
        organization_type="hospital",
    )
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
    referral_repository: ReferralRepository,
) -> None:
    mock_referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        data_domain="ImagingStudy",
        organization_type="Hospital",
    )
    mock_referral_2 = ReferralEntity(
        ura_number="0000124",
        pseudonym="ps-2",
        data_domain="MedicationStatement",
        organization_type="Hospital",
    )
    expected = [mock_referral_1, mock_referral_2]

    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_1)
        referral_repository.add_one(mock_referral_2)
        actual = referral_repository.find_many(organization_type="Hospital")

    assert expected == actual


def test_find_many_should_return_empty_list(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.find_many(
            pseudonym="differenet-pseudonym",
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

    assert actual == []


def test_find_should_return_one_referral(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        expected = [mock_referral_entity]

        actual = referral_repository.find(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
        )

        assert expected == actual


def test_find_should_return_two_referrals(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        another_referral = ReferralEntity(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number="00000123",
            organization_type=mock_referral_entity.data_domain,
        )
        referral_repository.add_one(mock_referral_entity)
        referral_2 = referral_repository.add_one(another_referral)
        expected = [mock_referral_entity, referral_2]

        actual = referral_repository.find(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
        )

        assert expected == actual


def test_find_should_return_two_referrals_from_different_organizations(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        different_org_referral = ReferralEntity(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number="00000123",
            organization_type="pharmacy",
        )
        referral_repository.add_one(mock_referral_entity)
        referral_2 = referral_repository.add_one(different_org_referral)
        expected = [mock_referral_entity, referral_2]

        actual = referral_repository.find(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            org_types=[
                mock_referral_entity.organization_type,
                referral_2.organization_type,
            ],
        )

        assert expected == actual


def test_find_should_return_empty_list_when_conditions_are_no_match(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        actual = referral_repository.find(pseudonym=mock_referral_entity.pseudonym, data_domain="SomeDataDomain")

        assert actual == []


def test_add_one_should_succeed(referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity) -> None:
    with referral_repository.db_session:
        actual = referral_repository.add_one(mock_referral_entity)

    assert mock_referral_entity == actual


def test_add_one_with_same_id_should_raise_exception(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        mock_referral_entity_2 = ReferralEntity(
            id=mock_referral_entity.id,
            pseudonym="some-other-pseudonym",
            data_domain="some-other-data-domain",
        )
        referral_repository.add_one(mock_referral_entity)
        with pytest.raises(SQLAlchemyError) as exec:
            referral_repository.add_one(mock_referral_entity_2)

        assert isinstance(exec.value, IntegrityError)


def test_add_one_with_same_unique_index_should_raise_exception(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        mock_2 = ReferralEntity(
            ura_number=mock_referral_entity.ura_number,
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
        )
        referral_repository.add_one(mock_referral_entity)
        with pytest.raises(SQLAlchemyError) as exec:
            referral_repository.add_one(mock_2)

        assert isinstance(exec.value, IntegrityError)


def test_delete_one_should_succeed(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        assert (
            referral_repository.exists(
                pseudonym=mock_referral_entity.pseudonym,
                data_domain=mock_referral_entity.data_domain,
                ura_number=mock_referral_entity.ura_number,
            )
            is True
        )

        referral_repository.delete_one(mock_referral_entity)

        assert (
            referral_repository.exists(
                pseudonym=mock_referral_entity.pseudonym,
                data_domain=mock_referral_entity.data_domain,
                ura_number=mock_referral_entity.ura_number,
            )
            is False
        )


def test_delete_one_should_raise_exception_when_does_not_exist(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        with pytest.raises(SQLAlchemyError):
            referral_repository.delete_one(mock_referral_entity)


def test_delete_with_only_ura_number_should_remove_all_recordss(
    referral_repository: ReferralRepository,
) -> None:
    referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        data_domain="ImagingStudy",
        organization_type="Hospital",
    )
    referral_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-2",
        data_domain="MedicationStatement",
        organization_type="Hospital",
    )
    # referral from a different provider
    referral_3 = ReferralEntity(
        ura_number="0000125",
        pseudonym="ps-3",
        data_domain="ImagingStudy",
        organization_type="Pharmacy",
    )
    with referral_repository.db_session:
        referral_repository.add_one(referral_1)
        referral_repository.add_one(referral_2)
        referral_repository.add_one(referral_3)

        referral_repository.delete(ura_number="0000123")

        assert referral_repository.exists(ura_number="0000123") is False
        assert referral_repository.exists(ura_number="0000125") is True


def test_delete_with_pseudonym_should_remove_all_records_for_patient(
    referral_repository: ReferralRepository,
) -> None:
    referral_1 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        data_domain="ImagingStudy",
        organization_type="Hospital",
    )
    referral_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-1",
        data_domain="MedicationStatement",
        organization_type="Hospital",
    )
    # referral from a different patient
    referral_3 = ReferralEntity(
        ura_number="0000123",
        pseudonym="ps-2",
        data_domain="ImagingStudy",
        organization_type="Pharmacy",
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
            dsn="postgresql+psycopg://postgres:connection@does_not_exists:12345/imaginary-db"
        )
    )
    referral_repository.db_session = db.get_db_session()
    with referral_repository.db_session:
        with pytest.raises(SQLAlchemyError):
            referral_repository.delete(ura_number="123")


def test_exists_should_return_true_if_record_is_there(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)

        exist = referral_repository.exists(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

        assert exist is True


def test_exists_should_return_false_if_record_is_not_there(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        exist = referral_repository.exists(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

        assert exist is False
