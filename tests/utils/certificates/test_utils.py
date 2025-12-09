import builtins
from unittest.mock import MagicMock, mock_open, patch

import pytest
from pytest import MonkeyPatch

from app.utils.certificates.utils import (
    _CERT_END,
    _CERT_START,
    enforce_cert_newlines,
    load_certificate,
)

PATCHED_MODULE = "app.utils.certificates.utils"


def test_enforce_cert_newlines_should_succeed() -> None:
    data = _CERT_START + "some-data" + _CERT_END
    expected = _CERT_START + "\nsome-data\n" + _CERT_END

    actual = enforce_cert_newlines(data)

    assert expected == actual


@patch(f"{PATCHED_MODULE}.x509")
@patch(f"{PATCHED_MODULE}.Path")
def test_load_ceritifcate_should_succeed(mock_path: MagicMock, mock_cert: MagicMock, monkeypatch: MonkeyPatch) -> None:
    fake_path = "/some/path"
    cert_data = "some-cert-data"
    cert = "some-cert"
    mock_path.exists.return_value = True
    mock_cert.load_pem_x509_certificate.return_value = cert
    monkeypatch.setattr(builtins, "open", mock_open(read_data=cert_data))

    actual = load_certificate(fake_path)

    assert cert == actual
    mock_cert.load_pem_x509_certificate.assert_called_once_with(cert_data.encode())


@patch(f"{PATCHED_MODULE}.Path.exists")
def test_load_ceritificate_should_raise_exception_when_file_not_found(
    mock_path: MagicMock,
) -> None:
    unknown_path = "/some/unknown/path"
    mock_path.return_value = False
    with pytest.raises(FileNotFoundError):
        load_certificate(unknown_path)


@patch(f"{PATCHED_MODULE}.x509")
@patch(f"{PATCHED_MODULE}.Path")
def test_load_certificate_should_raise_exception_when_error_occurs_from_cryptography(
    mock_path: MagicMock, mock_cert: MagicMock, monkeypatch: MonkeyPatch
) -> None:
    fake_path = "/some/path"
    cert_data = "some-cert-data"
    mock_path.exists.return_value = True
    opened_data = mock_open(read_data=str(cert_data))
    mock_cert.load_pem_x509_certificate.side_effect = Exception
    monkeypatch.setattr(builtins, "open", opened_data)
    with pytest.raises(ValueError):
        load_certificate(fake_path)
