import base64
import json

import pytest

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.pseudonym import PseudonymResponse
from app.services.exceptions import InvalidKeyInfoError, PseudonymError
from app.services.key_info import KeyInfoService
from app.services.pseudonym_resolver import PseudonymResolver


def _token(evaluated_output: str, blind_factor: str) -> str:
    raw = json.dumps({"evaluated_output": evaluated_output, "blind_factor": blind_factor}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture()
def resolver(key_info_service: KeyInfoService) -> PseudonymResolver:
    return PseudonymResolver(crypto_client=CryptoServiceApiClientMock(), key_info_service=key_info_service)


def test_resolve_jwe_exchanges_with_active_key(resolver: PseudonymResolver, key_info_service: KeyInfoService) -> None:
    key = key_info_service.add_one("nvi-label", "AES_CBC")

    result = resolver.resolve_jwe(jwe="JWE", blind_factor="BF")

    # mock echoes "{jwe}:{blind_factor}"
    assert result.response.encrypted_pseudonym == "JWE:BF"
    assert result.key_id == key.id
    assert result.encrypted.value == "abcdefghijklmnopJWE:BF"


def test_resolve_token_decodes_then_exchanges(resolver: PseudonymResolver, key_info_service: KeyInfoService) -> None:
    key = key_info_service.add_one("nvi-label", "AES_CBC")

    result = resolver.resolve_token(_token("JWE", "BF"))

    assert result.response.encrypted_pseudonym == "JWE:BF"
    assert result.key_id == key.id


def test_resolve_token_raises_pseudonym_error_on_malformed_token(
    resolver: PseudonymResolver, key_info_service: KeyInfoService
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")

    with pytest.raises(PseudonymError):
        resolver.resolve_token("not-a-valid-token!!!")


def test_resolve_jwe_propagates_invalid_key_info_when_no_active_key(resolver: PseudonymResolver) -> None:
    with pytest.raises(InvalidKeyInfoError):
        resolver.resolve_jwe(jwe="JWE", blind_factor="BF")


def test_resolve_token_propagates_invalid_key_info_when_no_active_key(resolver: PseudonymResolver) -> None:
    # A missing active key is an infrastructure fault (503), not a bad pseudonym (400).
    with pytest.raises(InvalidKeyInfoError):
        resolver.resolve_token(_token("JWE", "BF"))


def test_resolve_token_raises_pseudonym_error_when_token_lacks_expected_fields(
    resolver: PseudonymResolver, key_info_service: KeyInfoService
) -> None:
    # Decodes cleanly but carries the wrong shape - still the client's fault, so 400.
    key_info_service.add_one("nvi-label", "AES_CBC")
    token = base64.urlsafe_b64encode(json.dumps({"something_else": "x"}).encode()).decode().rstrip("=")

    with pytest.raises(PseudonymError):
        resolver.resolve_token(token)


def test_resolve_token_propagates_crypto_service_failures(key_info_service: KeyInfoService) -> None:
    # A crypto-service outage must not be reported to the client as an invalid
    # pseudonym (400); only a token that fails to decode is the client's fault.
    class FailingCryptoClient(CryptoServiceApiClientMock):
        def exchange(self, jwe: str, blind_factor: str, label: str, mechanism: str) -> PseudonymResponse:
            raise ConnectionError("crypto service unreachable")

    key_info_service.add_one("nvi-label", "AES_CBC")
    resolver = PseudonymResolver(crypto_client=FailingCryptoClient(), key_info_service=key_info_service)

    with pytest.raises(ConnectionError):
        resolver.resolve_token(_token("JWE", "BF"))


def test_encrypted_pseudonym_is_computed_once(resolver: PseudonymResolver, key_info_service: KeyInfoService) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")

    resolved = resolver.resolve_jwe(jwe="JWE", blind_factor="BF")

    assert resolved.encrypted is resolved.encrypted
