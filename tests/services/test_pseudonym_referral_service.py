import logging
from typing import Any

import pytest
from gfmodules.logging import LogEvent

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.logging.events import Log
from app.models.pseudonym import OprfPseudonym, PseudonymResponse
from app.models.ura import UraNumber
from app.services.exceptions import InvalidKeyInfoError, PseudonymExchangeError
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

REQUESTING_URA = UraNumber("00000456")
SOURCE = "SomeDevice"
OTHER_SOURCE = "OtherDevice"
PSEUDONYM = OprfPseudonym(pseudonym="JWE", oprf_key="BF")
OTHER_PSEUDONYM = OprfPseudonym(pseudonym="OTHER", oprf_key="BF")


class FailingCryptoClient(CryptoServiceApiClientMock):
    def exchange(self, pseudonym: OprfPseudonym, label: str, mechanism: str) -> PseudonymResponse:
        raise RuntimeError("boom")


class RejectingCryptoClient(CryptoServiceApiClientMock):
    def exchange(self, pseudonym: OprfPseudonym, label: str, mechanism: str) -> PseudonymResponse:
        raise PseudonymExchangeError("Invalid pseudonym or oprf_key")


def logged_fields(caplog: pytest.LogCaptureFixture, event: LogEvent) -> list[dict[str, Any]]:
    return [vars(record) for record in caplog.records if getattr(record, "event_id", None) == event.event_id]


def _service_with(
    crypto_client: CryptoServiceApiClientMock, referral_service: ReferralService, key_info_service: KeyInfoService
) -> PseudonymReferralService:
    key_info_service.add_one("nvi-label", "AES_CBC")
    resolver = PseudonymResolver(crypto_client=crypto_client, key_info_service=key_info_service)
    return PseudonymReferralService(referral_service=referral_service, pseudonym_resolver=resolver)


@pytest.fixture
def failing_service(referral_service: ReferralService, key_info_service: KeyInfoService) -> PseudonymReferralService:
    return _service_with(FailingCryptoClient(), referral_service, key_info_service)


@pytest.fixture
def rejecting_service(referral_service: ReferralService, key_info_service: KeyInfoService) -> PseudonymReferralService:
    return _service_with(RejectingCryptoClient(), referral_service, key_info_service)


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
    rejecting_service: PseudonymReferralService,
    ura_number: UraNumber,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(PseudonymExchangeError):
        rejecting_service.register(PSEUDONYM, ura_number, SOURCE)

    (fields,) = logged_fields(caplog, Log.REFERRAL_REGISTRATION_FAILED)
    assert fields["http_status"] == 400


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

    _, referrals = pseudonym_referral_service.localize(PSEUDONYM, REQUESTING_URA)

    assert [r.ura_number for r in referrals] == [str(ura_number)]


def test_localize_logs_a_failure_when_the_pseudonym_is_invalid(
    rejecting_service: PseudonymReferralService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(PseudonymExchangeError):
        rejecting_service.localize(PSEUDONYM, REQUESTING_URA)

    (fields,) = logged_fields(caplog, Log.LOCALIZATION_FAILED)
    assert fields["levelno"] == logging.WARNING
    assert fields["http_status"] == 400


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
