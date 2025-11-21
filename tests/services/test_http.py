from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError, Timeout

from app.services.http import HttpService

PATCHED_MODULE = "app.services.http.request"


@patch(PATCHED_MODULE)
def test_do_request_should_succeed(response: MagicMock, http_service: HttpService) -> None:
    data = {"message": "hello world"}
    mock_call = MagicMock()
    mock_call.status_code = 200
    mock_call.json.return_value = data
    response.return_value = mock_call

    actual = http_service.do_request("GET")

    assert actual.status_code == 200
    assert actual.json() == data


@patch(PATCHED_MODULE)
def test_do_request_raise_excetion_with_timeout(response: MagicMock, http_service: HttpService) -> None:
    response.side_effect = Timeout
    with pytest.raises(Timeout):
        http_service.do_request("GET")


@patch(PATCHED_MODULE)
def test_do_request_raise_excetion_with_connection_error(response: MagicMock, http_service: HttpService) -> None:
    response.side_effect = ConnectionError
    with pytest.raises(ConnectionError):
        http_service.do_request("GET")


@patch(PATCHED_MODULE)
def test_do_request_raise_excetion_with_general_http_error(response: MagicMock, http_service: HttpService) -> None:
    response.side_effect = HTTPError
    with pytest.raises(HTTPError):
        http_service.do_request("GET")
