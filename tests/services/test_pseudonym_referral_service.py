from app.models.pseudonym import OprfPseudonym
from app.models.ura import UraNumber
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService

REQUESTING_URA = UraNumber("00000456")
SOURCE = "SomeDevice"
PSEUDONYM = OprfPseudonym(jwe="JWE", blind_factor="BF")


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

    referrals = pseudonym_referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert [r.ura_number for r in referrals] == [str(ura_number)]


def test_query_and_delete_resolve_the_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    assert len(pseudonym_referral_service.query(ura_number, pseudonym=PSEUDONYM)) == 1
    assert pseudonym_referral_service.delete_many(ura_number, pseudonym=PSEUDONYM) == 1
