from json import JSONDecodeError
from unittest.mock import MagicMock

import pytest
from requests.exceptions import ConnectionError, Timeout

from app.models.pseudonym import Pseudonym
from app.services.crypto_service_api_client import CryptoServiceApiClient


@pytest.fixture()
def http_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def crypto_client(http_mock: MagicMock) -> CryptoServiceApiClient:
    client = CryptoServiceApiClient.__new__(CryptoServiceApiClient)
    client._http = http_mock
    return client


def test_exchange_returns_hashed_pseudonym(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.json.return_value = {"hashed_pseudonym": "abc123"}
    http_mock.do_request.return_value = response

    result = crypto_client.exchange("some-jwe", "some-blind-factor")

    assert result == Pseudonym(value="abc123")
    http_mock.do_request.assert_called_once_with(
        method="POST",
        sub_route="decrypt_and_hash",
        data={"jwe": "some-jwe", "blind_factor": "some-blind-factor"},
    )


def test_exchange_raises_on_connection_error(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    http_mock.do_request.side_effect = ConnectionError

    with pytest.raises(ConnectionError):
        crypto_client.exchange("jwe", "bf")


def test_exchange_raises_on_timeout(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    http_mock.do_request.side_effect = Timeout

    with pytest.raises(ConnectionError):
        crypto_client.exchange("jwe", "bf")


def test_exchange_raises_on_invalid_json(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.json.side_effect = JSONDecodeError("err", "", 0)
    http_mock.do_request.return_value = response

    with pytest.raises(ValueError):
        crypto_client.exchange("jwe", "bf")


def test_exchange_raises_on_missing_key(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.json.return_value = {"unexpected_key": "value"}
    http_mock.do_request.return_value = response

    with pytest.raises(ValueError):
        crypto_client.exchange("jwe", "bf")


def test_exchange_raises_on_http_error(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = Exception("500")
    http_mock.do_request.return_value = response

    with pytest.raises(Exception):
        crypto_client.exchange("jwe", "bf")


def test_is_healthy_returns_true_on_200(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    http_mock.do_request.return_value = response

    assert crypto_client.is_healthy() is True
    http_mock.do_request.assert_called_once_with(method="GET", sub_route="health")


def test_is_healthy_returns_false_on_non_200(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 503
    http_mock.do_request.return_value = response

    assert crypto_client.is_healthy() is False


def test_is_healthy_returns_false_on_connection_error(
    crypto_client: CryptoServiceApiClient, http_mock: MagicMock
) -> None:
    http_mock.do_request.side_effect = ConnectionError

    assert crypto_client.is_healthy() is False


def test_is_healthy_returns_false_on_timeout(crypto_client: CryptoServiceApiClient, http_mock: MagicMock) -> None:
    http_mock.do_request.side_effect = Timeout

    assert crypto_client.is_healthy() is False
