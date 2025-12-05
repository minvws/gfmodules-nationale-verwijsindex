import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository


@pytest.fixture()
def mock_referral_entity() -> ReferralEntity:
    return ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        data_domain="ImagingStudy",
        encrypted_lmr_id="some-id",
        lmr_endpoint="http://example.com",
    )


def test_query_referral_should_return_one_item(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        expected = [mock_referral_entity]

        actual = referral_repository.query_referrals(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

    assert expected == actual


def test_query_referral_should_return_two_item(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    mock_referral_entity_2 = ReferralEntity(
        ura_number="0000123",
        pseudonym="some-pseudonym",
        data_domain="MedicationStatement",
        encrypted_lmr_id="some-id",
        lmr_endpoint="http://example.com",
    )
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        referral_repository.add_one(mock_referral_entity_2)
        expected = [mock_referral_entity, mock_referral_entity_2]

        actual = referral_repository.query_referrals(
            pseudonym=mock_referral_entity.pseudonym,
            ura_number=mock_referral_entity.ura_number,
        )

    assert expected == actual


def test_query_referral_should_return_empty_list(
    referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)

        actual = referral_repository.query_referrals(
            pseudonym="differenet-pseudonym",
            data_domain=mock_referral_entity.data_domain,
            ura_number=mock_referral_entity.ura_number,
        )

    assert actual == []


def test_add_one_should_succeed(referral_repository: ReferralRepository, mock_referral_entity: ReferralEntity) -> None:
    with referral_repository.db_session:
        actual = referral_repository.add_one(mock_referral_entity)

    assert mock_referral_entity == actual


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
