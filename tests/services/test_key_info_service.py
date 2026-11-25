import pytest

from app.config import ConfigCryptoServiceApi
from app.container import create_key_info_service
from app.db.db import Database
from app.db.models.key_info import KeyInfoEntity
from app.db.models.referral import ReferralEntity
from app.db.repository.key_info_repository import KeyInfoRepository
from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.pseudonym import OprfPseudonym
from app.models.ura import UraNumber
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService
from tests.conftest import OrganizationFor

DISABLED_CRYPTO_SERVICE = ConfigCryptoServiceApi(enabled=False, endpoint="http://crypto-service")


def test_registration_works_with_the_crypto_service_disabled(
    database: Database, referral_service: ReferralService, ura_number: UraNumber
) -> None:
    resolver = PseudonymResolver(
        crypto_client=CryptoServiceApiClientMock(),
        key_info_service=create_key_info_service(DISABLED_CRYPTO_SERVICE, database),
    )
    service = PseudonymReferralService(referral_service=referral_service, pseudonym_resolver=resolver)

    referral, created = service.register(OprfPseudonym(pseudonym="JWE", oprf_key="BF"), ura_number, "SomeDevice")

    assert created is True
    assert referral.key_id is not None


def test_crypto_service_disabled_stores_one_key_and_reuses_it(database: Database) -> None:
    key_info_service = create_key_info_service(DISABLED_CRYPTO_SERVICE, database)

    first = key_info_service.get_active_key()
    second = key_info_service.get_active_key()

    assert first.id is not None
    assert second.id == first.id
    with database.get_db_session() as session:
        assert len(session.get_repository(KeyInfoRepository).find_many()) == 1


def test_add_one_should_succeed(key_info_service: KeyInfoService, mock_key_info: KeyInfoEntity) -> None:
    actual = key_info_service.add_one(label=mock_key_info.label, mechanism=mock_key_info.mechanism)
    for c in actual.__table__.columns:
        if c.name == "id" or c.name == "created_at":
            continue

        expected_attr = getattr(mock_key_info, c.name)
        actual_attr = getattr(actual, c.name)
        assert expected_attr == actual_attr


def test_add_one_should_raise_on_dupicates(key_info_service: KeyInfoService, mock_key_info: KeyInfoEntity) -> None:
    key_info_service.add_one(mock_key_info.label, mock_key_info.mechanism)
    with pytest.raises(ConflictError):
        key_info_service.add_one(mock_key_info.label, mock_key_info.mechanism)


def test_get_one_should_succeed(key_info_service: KeyInfoService, mock_key_info: KeyInfoEntity) -> None:
    expected = key_info_service.add_one(mock_key_info.label, mock_key_info.mechanism)
    actual = key_info_service.get_one(expected.label)

    for c in actual.__table__.columns:
        expected_attr = getattr(expected, c.name)
        actual_attr = getattr(actual, c.name)
        assert expected_attr == actual_attr


def test_get_one_should_raise_exception_when_not_found(
    key_info_service: KeyInfoService,
) -> None:
    with pytest.raises(NotFoundError):
        key_info_service.get_one("AES_GCM")


def test_get_many_should_succeed(key_info_service: KeyInfoService) -> None:
    key_info_service.add_one("label-1", "AES_CBC")
    key_info_service.add_one("label-2", "AES_GCC")
    results = key_info_service.get_many()
    assert len(results) == 2


def test_get_many_should_return_empty_list(key_info_service: KeyInfoService) -> None:
    results = key_info_service.get_many()
    assert len(results) == 0


def test_get_many_should_filter_by_mechanism(key_info_service: KeyInfoService) -> None:
    key_info_service.add_one("label-1", "AES_CBC")
    key_info_service.add_one("label-2", "AES_CBC")
    key_info_service.add_one("label-3", "AES_GCC")

    cbc_results = key_info_service.get_many("AES_CBC")
    gcc_reseults = key_info_service.get_many("AES_GCC")

    assert len(cbc_results) == 2
    assert len(gcc_reseults) == 1


def test_delete_one_should_succeed(key_info_service: KeyInfoService, mock_key_info: KeyInfoEntity) -> None:
    key_info_service.add_one(mock_key_info.label, mock_key_info.mechanism)
    key_info_service.delete_one(mock_key_info.label)
    with pytest.raises(NotFoundError):
        key_info_service.get_one(mock_key_info.label)


def test_delete_should_raise_when_no_label_exists(
    key_info_service: KeyInfoService,
) -> None:
    with pytest.raises(NotFoundError):
        key_info_service.delete_one("some-label")


def test_delete_should_raise_when_key_has_referrals(
    key_info_service: KeyInfoService,
    mock_key_info: KeyInfoEntity,
    database: Database,
    organization_for: OrganizationFor,
) -> None:
    new_key = key_info_service.add_one(mock_key_info.label, mock_key_info.mechanism)
    with database.get_db_session() as session:
        mock_referral = ReferralEntity(
            organization=organization_for("90000101"),
            pseudonym="some-pseudonym",
            source="some-source",
            key_id=new_key.id,
        )
        session.add(mock_referral)
        session.commit()

        key_info_repo = session.get_repository(KeyInfoRepository)
        updated_key = key_info_repo.find_one(new_key.label)

        assert updated_key is not None
        assert updated_key.has_referrals is True

    with pytest.raises(ForbiddenError):
        key_info_service.delete_one(updated_key.label)
