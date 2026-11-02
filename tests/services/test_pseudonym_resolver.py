import pytest

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.pseudonym import OprfPseudonym, PseudonymResponse
from app.services.exceptions import InvalidKeyInfoError
from app.services.key_info import KeyInfoService
from app.services.pseudonym_resolver import PseudonymResolver

OPRF_PSEUDONYM = OprfPseudonym(jwe="JWE", blind_factor="BF")


@pytest.fixture()
def resolver(key_info_service: KeyInfoService) -> PseudonymResolver:
    return PseudonymResolver(crypto_client=CryptoServiceApiClientMock(), key_info_service=key_info_service)


def test_resolve_exchanges_with_active_key(resolver: PseudonymResolver, key_info_service: KeyInfoService) -> None:
    key = key_info_service.add_one("nvi-label", "AES_CBC")

    result = resolver.resolve(OPRF_PSEUDONYM)

    # mock echoes "{jwe}:{blind_factor}"
    assert result.response.encrypted_pseudonym == "JWE:BF"
    assert result.key_id == key.id
    assert result.encrypted.value == "abcdefghijklmnopJWE:BF"


def test_resolve_propagates_invalid_key_info_when_no_active_key(resolver: PseudonymResolver) -> None:
    with pytest.raises(InvalidKeyInfoError):
        resolver.resolve(OPRF_PSEUDONYM)


def test_resolve_propagates_crypto_service_failures(key_info_service: KeyInfoService) -> None:
    class FailingCryptoClient(CryptoServiceApiClientMock):
        def exchange(self, pseudonym: OprfPseudonym, label: str, mechanism: str) -> PseudonymResponse:
            raise ConnectionError("crypto service unreachable")

    key_info_service.add_one("nvi-label", "AES_CBC")
    resolver = PseudonymResolver(crypto_client=FailingCryptoClient(), key_info_service=key_info_service)

    with pytest.raises(ConnectionError):
        resolver.resolve(OPRF_PSEUDONYM)


def test_encrypted_pseudonym_is_computed_once(resolver: PseudonymResolver, key_info_service: KeyInfoService) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")

    resolved = resolver.resolve(OPRF_PSEUDONYM)

    assert resolved.encrypted is resolved.encrypted
