import pytest
from cryptography.x509 import Certificate

from app.utils.certificates.utils import (
    _CERT_END,
    _CERT_START,
    create_certificate,
    enforce_cert_newlines,
    load_certificate,
    load_one_certificate_file,
)


def test_enforce_cert_newlines_should_succeed() -> None:
    data = _CERT_START + "some-data" + _CERT_END
    expected = _CERT_START + "\nsome-data\n" + _CERT_END

    actual = enforce_cert_newlines(data)

    assert expected == actual


def test_load_one_certificate_path_should_succeed(certificate_str: str, cert_path: str) -> None:
    actual = load_one_certificate_file(cert_path)

    assert actual == certificate_str


def test_load_one_cerftificate_should_raise_exception_when_a_dir_is_given(
    cert_dir: str,
) -> None:
    with pytest.raises(IsADirectoryError):
        load_one_certificate_file(cert_dir)


def test_load_one_certificate_should_raise_exception_when_file_not_found() -> None:
    incorrect_file_path = "some/incorrec-path/wrong-file"
    with pytest.raises(FileNotFoundError):
        load_one_certificate_file(incorrect_file_path)


def test_create_certificate_should_succeed(certificate_str: str, certificate: Certificate) -> None:
    expected = create_certificate(certificate_str)

    assert expected == certificate


def test_create_ceritifcate_should_raise_exception_with_incorrect_x509_cert() -> None:
    cert = "some-malformed-x509-cert"
    with pytest.raises(Exception):
        create_certificate(cert)


def test_load_certificate_should_succeed(cert_path: str, certificate: Certificate) -> None:
    actual = load_certificate(cert_path)

    assert certificate == actual
