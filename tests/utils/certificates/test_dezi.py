import builtins
from unittest.mock import MagicMock, mock_open, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import Certificate
from pytest import MonkeyPatch

from app.jwt_validator import DeziSigningCert
from app.models.ura import UraNumber
from app.utils.certificates.dezi import (
    DeziCertExceptin,
    get_ura_from_cert,
    load_dezi_signing_certificates,
    verify_and_get_uzi_cert,
)
from app.utils.certificates.utils import load_certificate

PATCHED_MODULE = "app.utils.certificates.dezi"


@pytest.fixture()
def certificate() -> Certificate:
    return load_certificate("tests/secrets/mock-server-cert.crt")


@pytest.fixture()
def certificate_str() -> str:
    with open("tests/secrets/mock-server-cert.crt", "r") as f:
        data = f.read()

    return data


def test_verify_and_get_uzi_cert_should_succeed(
    certificate_str: str,
) -> None:
    expected = UraNumber("90000123")
    actual = verify_and_get_uzi_cert(certificate_str)

    assert expected == actual


@patch(f"{PATCHED_MODULE}.verify_and_get_uzi_cert")
def test_get_ura_from_cert_should_succeed(
    mock_ura_number: MagicMock, monkeypatch: MonkeyPatch
) -> None:
    expected = UraNumber("00000123")
    mock_ura_number.return_value = expected
    monkeypatch.setattr(builtins, "open", mock_open(read_data=str(expected)))
    actual = get_ura_from_cert("/some/path")

    assert expected == actual


def test_get_ura_from_cert_should_fail_with_wrong_cert_path(
    monkeypatch: MonkeyPatch,
) -> None:
    mocked_open = mock_open(read_data="some-cert")
    mocked_open.side_effect = IOError
    monkeypatch.setattr(builtins, "open", mocked_open)
    with pytest.raises(DeziCertExceptin):
        get_ura_from_cert("somne/path")


@patch(f"{PATCHED_MODULE}.verify_and_get_uzi_cert")
def test_get_ura_from_cert_should_raise_exception_with_invalid_uzi_cert(
    mock_ura_number: MagicMock, monkeypatch: MonkeyPatch
) -> None:
    mock_ura_number.side_effect = DeziCertExceptin
    monkeypatch.setattr(builtins, "open", mock_open(read_data="some-data"))
    with pytest.raises(DeziCertExceptin):
        get_ura_from_cert("/some/path")


# @patch(f"{PATCHED_MODULE}.base64")
# @patch(f"{PATCHED_MODULE}.Path")
# @patch(f"{PATCHED_MODULE}.load_certificate")
# def test_load_dezi_signing_certificates_should_succeed(
#     mock_cert: MagicMock, mock_path: MagicMock, mock_base64: MagicMock
# ) -> None:
#     fake_path = "/some/path"
#     mock_path_module = MagicMock()
#     mock_path_module.exists.return_value = True
#     mock_path_module.iterdir.return_value = ["cert_1"]
#     mock_path.return_value = mock_path_module
#
#     mock_cert_module = MagicMock(spec=Certificate, return_value="some-cert")
#     mock_cert_module.fingerprint.return_value = "some-fingerprint"
#     mock_pub_key = rsa.generate_private_key(public_exponent=3, key_size=1024).public_key()
#     mock_cert_module.public_key.return_value = mock_pub_key
#     mock_cert.return_value = mock_cert_module
#     mock_base64.return_value = "=some-base64-encoded-data="
#
#     expected = [
#         DeziSigningCert(
#             certificate=mock_cert,
#             x5t="some-base64-encoded-data",
#             public_key=mock_pub_key,
#         )
#     ]
#
#     actual = load_dezi_signing_certificates(fake_path)
#
#     assert expected == actual
