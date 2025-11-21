import builtins
from unittest.mock import MagicMock, mock_open, patch

import pytest
from pytest import MonkeyPatch
from uzireader.uzi import UziException

from app.models.ura import UraNumber
from app.ura.uzi_cert_common import (
    _CERT_END,
    _CERT_START,
    UraException,
    _enforce_cert_newlines,
    get_ura_from_cert,
    verify_and_get_uzi_cert,
)

PATCHED_MODULE = "app.ura.uzi_cert_common"


def test_enforce_cert_newlines_should_succeed() -> None:
    data = _CERT_START + "some-data" + _CERT_END
    expected = _CERT_START + "\nsome-data\n" + _CERT_END

    actual = _enforce_cert_newlines(data)

    assert expected == actual


@patch(f"{PATCHED_MODULE}.UziServer")
@patch(f"{PATCHED_MODULE}._enforce_cert_newlines")
def test_verify_and_get_uzi_cert_should_succeed(mock_cert: MagicMock, mock_uzi_server: MagicMock) -> None:
    expected_ura = UraNumber("00000123")
    mock_cert.return_value = "some-cert"
    mock_uzi_server.return_value = {"SubscriberNumber": expected_ura.value}

    actual = verify_and_get_uzi_cert(mock_cert)

    assert expected_ura == actual


@patch(f"{PATCHED_MODULE}.verify_and_get_uzi_cert")
def test_get_ura_should_succeed(mock_ura_number: MagicMock, monkeypatch: MonkeyPatch) -> None:
    expected = "00000123"
    mock_ura_number.return_value = UraNumber(expected)
    monkeypatch.setattr(builtins, "open", mock_open(read_data=expected))
    actual = get_ura_from_cert("/some/path")

    assert expected == actual


def test_get_ura_should_fail_with_wrong_cert_path(monkeypatch: MonkeyPatch) -> None:
    mocked_open = mock_open(read_data="some-cert")
    mocked_open.side_effect = IOError
    monkeypatch.setattr(builtins, "open", mocked_open)
    with pytest.raises(UraException):
        get_ura_from_cert("somne/path")


@patch(f"{PATCHED_MODULE}.verify_and_get_uzi_cert")
def test_get_ura_should_raise_exception_with_invalid_uzi_cert(
    mock_ura_number: MagicMock, monkeypatch: MonkeyPatch
) -> None:
    mock_ura_number.side_effect = UziException
    monkeypatch.setattr(builtins, "open", mock_open(read_data="some-data"))
    with pytest.raises(UraException):
        get_ura_from_cert("/some/path")
