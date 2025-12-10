import base64

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509 import Certificate

from app.jwt_validator import DeziSigningCert
from app.models.ura import UraNumber
from app.utils.certificates.dezi import (
    DeziCertException,
    get_ura_from_cert,
    load_dezi_signing_certificates,
    verify_and_get_uzi_cert,
)


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
    with pytest.raises(DeziCertException):
        get_ura_from_cert(incorrect_path)


def test_load_dezi_signing_certificates_should_succeed(cert_dir: str, certificate: Certificate) -> None:
    sha1_fingerprint = certificate.fingerprint(hashes.SHA1())  # NOSONAR
    x5t = base64.urlsafe_b64encode(sha1_fingerprint).decode("utf-8")
    x5t = x5t.rstrip("=")
    public_key = certificate.public_key()
    assert isinstance(public_key, RSAPublicKey)
    dezi_signing_cert = DeziSigningCert(certificate=certificate, public_key=public_key, x5t=x5t)
    expected = [dezi_signing_cert]

    actual = load_dezi_signing_certificates(cert_dir)

    assert expected == actual
