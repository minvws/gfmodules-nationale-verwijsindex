from app.models.pseudonym import OprfPseudonym
from app.models.ura import UraNumber
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService

REQUESTING_URA = UraNumber("00000456")
SOURCE = "SomeDevice"
OTHER_SOURCE = "OtherDevice"
PSEUDONYM = OprfPseudonym(jwe="JWE", blind_factor="BF")
OTHER_PSEUDONYM = OprfPseudonym(jwe="OTHER", blind_factor="BF")


def test_register_stores_the_resolved_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info = key_info_service.add_one("nvi-label", "AES_CBC")

    referral, created = pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    assert created is True
    assert referral.pseudonym == "abcdefghijklmnopJWE:BF"
    assert referral.key_id == key_info.id


def test_localize_finds_referrals_of_the_resolved_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    _, referrals = pseudonym_referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert [r.ura_number for r in referrals] == [str(ura_number)]


def test_query_finds_referrals_of_the_resolved_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)
    pseudonym_referral_service.register(OTHER_PSEUDONYM, ura_number, SOURCE)

    total, referrals = pseudonym_referral_service.query(ura_number, pseudonym=PSEUDONYM)

    assert total == 1
    assert [r.pseudonym for r in referrals] == ["abcdefghijklmnopJWE:BF"]


def test_query_without_pseudonym_finds_all_referrals_of_the_ura(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)
    pseudonym_referral_service.register(OTHER_PSEUDONYM, ura_number, SOURCE)

    total, _ = pseudonym_referral_service.query(ura_number)

    assert total == 2


def test_delete_many_removes_referrals_of_the_resolved_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)
    pseudonym_referral_service.register(OTHER_PSEUDONYM, ura_number, SOURCE)

    assert pseudonym_referral_service.delete_many(ura_number, pseudonym=PSEUDONYM) == 1
    assert pseudonym_referral_service.query(ura_number)[0] == 1


def test_delete_many_without_pseudonym_removes_referrals_of_the_source(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)
    pseudonym_referral_service.register(OTHER_PSEUDONYM, ura_number, SOURCE)
    pseudonym_referral_service.register(PSEUDONYM, ura_number, OTHER_SOURCE)

    assert pseudonym_referral_service.delete_many(ura_number, source=SOURCE) == 2
    assert pseudonym_referral_service.query(ura_number)[0] == 1
