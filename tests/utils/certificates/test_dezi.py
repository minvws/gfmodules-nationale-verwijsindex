import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509 import Certificate

from app.models.dezi import DeziSigningCert
from app.models.ura import UraNumber
from app.utils.certificates.dezi import (
    get_ura_from_cert,
    load_dezi_signing_certificates,
    verify_and_get_uzi_cert,
)
from app.utils.certificates.exceptions import DeziCertError
from app.utils.certificates.utils import get_x5t_from_certificate


def test_verify_and_get_uzi_cert_should_succeed(certificate_str: str, ura_number: UraNumber) -> None:
    actual = verify_and_get_uzi_cert(certificate_str)

    assert ura_number == actual


def test_verify_and_get_uzi_cert_should_raise_exception_with_invalid_certs() -> None:
    incorrect_cert = "some-incorrect-cert"
    with pytest.raises(ValueError):
        verify_and_get_uzi_cert(incorrect_cert)


def test_get_ura_from_cert_should_succeed(ura_number: UraNumber, cert_path: str) -> None:
    actual = get_ura_from_cert(cert_path)

    assert ura_number == actual


def test_get_ura_from_cert_should_raise_exception_with_incorret_path() -> None:
    incorrect_path = "some/incorrect_path"
    with pytest.raises(DeziCertError):
        get_ura_from_cert(incorrect_path)


def test_load_dezi_signing_certificates_should_succeed(cert_dir: str, certificate: Certificate) -> None:
    x5t = get_x5t_from_certificate(certificate)
    public_key = certificate.public_key()
    assert isinstance(public_key, RSAPublicKey)
    dezi_signing_cert = DeziSigningCert(certificate=certificate, public_key=public_key, x5t=x5t)
    expected = [dezi_signing_cert]

    actual = load_dezi_signing_certificates(cert_dir)

    assert expected == actual
