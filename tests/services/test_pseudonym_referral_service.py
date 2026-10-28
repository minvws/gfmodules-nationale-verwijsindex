import logging
from typing import Any

import pytest
from gfmodules.logging import LogEvent

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.logging.events import Log
from app.models.pseudonym import OprfPseudonym, PseudonymResponse, PseudonymToken
from app.models.ura import UraNumber
from app.services.exceptions import InvalidKeyInfoError, PseudonymError
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

REQUESTING_URA = UraNumber("00000456")
SOURCE = "SomeDevice"
PSEUDONYM = OprfPseudonym(jwe="JWE", blind_factor="BF")
INVALID_TOKEN = PseudonymToken("not-a-valid-token!!!")


class FailingCryptoClient(CryptoServiceApiClientMock):
    def exchange(self, jwe: str, blind_factor: str, label: str, mechanism: str) -> PseudonymResponse:
        raise RuntimeError("boom")


def logged_fields(caplog: pytest.LogCaptureFixture, event: LogEvent) -> list[dict[str, Any]]:
    return [vars(record) for record in caplog.records if getattr(record, "event_id", None) == event.event_id]


@pytest.fixture
def failing_service(referral_service: ReferralService, key_info_service: KeyInfoService) -> PseudonymReferralService:
    key_info_service.add_one("nvi-label", "AES_CBC")
    resolver = PseudonymResolver(crypto_client=FailingCryptoClient(), key_info_service=key_info_service)
    return PseudonymReferralService(referral_service=referral_service, pseudonym_resolver=resolver)


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


def test_register_logs_a_failure_when_the_pseudonym_is_invalid(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")

    with caplog.at_level(logging.INFO), pytest.raises(PseudonymError):
        pseudonym_referral_service.register(INVALID_TOKEN, ura_number, SOURCE)

    (fields,) = logged_fields(caplog, Log.REFERRAL_REGISTRATION_FAILED)
    assert fields["http_status"] == 422


def test_register_does_not_log_an_expected_failure(
    pseudonym_referral_service: PseudonymReferralService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(InvalidKeyInfoError):
        pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    assert logged_fields(caplog, Log.REFERRAL_REGISTRATION_FAILED) == []


def test_localize_finds_referrals_of_the_resolved_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    referrals = pseudonym_referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert [r.ura_number for r in referrals] == [str(ura_number)]


def test_localize_logs_a_failure_when_the_pseudonym_is_invalid(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")

    with caplog.at_level(logging.INFO), pytest.raises(PseudonymError):
        pseudonym_referral_service.localize(INVALID_TOKEN, REQUESTING_URA)

    (fields,) = logged_fields(caplog, Log.LOCALIZATION_FAILED)
    assert fields["levelno"] == logging.WARNING
    assert fields["http_status"] == 422


def test_localize_logs_an_error_when_it_breaks(
    failing_service: PseudonymReferralService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        failing_service.localize(PSEUDONYM, REQUESTING_URA)

    (fields,) = logged_fields(caplog, Log.LOCALIZATION_ERROR)
    assert fields["levelno"] == logging.ERROR
    assert fields["http_status"] == 500
    assert fields["error_reason"] == "boom"


def test_localize_does_not_log_an_expected_failure(
    pseudonym_referral_service: PseudonymReferralService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(InvalidKeyInfoError):
        pseudonym_referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert logged_fields(caplog, Log.LOCALIZATION_FAILED) == []


def test_query_and_delete_resolve_the_pseudonym(
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
    ura_number: UraNumber,
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    pseudonym_referral_service.register(PSEUDONYM, ura_number, SOURCE)

    assert len(pseudonym_referral_service.query(ura_number, pseudonym=PSEUDONYM)) == 1
    assert pseudonym_referral_service.delete_many(ura_number, pseudonym=PSEUDONYM) == 1
