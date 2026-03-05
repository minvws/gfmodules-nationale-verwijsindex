from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from app.exceptions.fhir_exception import FHIRException
from app.models.pseudonym import Pseudonym
from app.routers.data_reference import exchange_oprf
from app.services.prs.exception import PseudonymError
from app.services.prs.pseudonym_service import PseudonymService


def test_exchange_oprf_should_raise_400_when_pseudonym_request_is_invalid() -> None:
    pseudonym_service = MagicMock(spec=PseudonymService)
    pseudonym_service.exchange.side_effect = PseudonymError("Invalid pseudonym request")

    with pytest.raises(FHIRException) as exc:
        exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe="invalid-jwe",
            blind_factor="invalid-oprf-key",
        )

    detail = cast(dict[str, Any], exc.value.detail)
    issue = detail["issue"][0]
    assert exc.value.status_code == 400
    assert issue["code"] == "invalid"
    assert issue["details"]["text"] == "Invalid pseudonym request"
    assert issue["expression"] == ["NVIDataReference.subject"]


def test_exchange_oprf_should_raise_500_when_pseudonym_exchange_fails_unexpectedly() -> None:
    pseudonym_service = MagicMock(spec=PseudonymService)
    pseudonym_service.exchange.side_effect = RuntimeError("unexpected failure")

    with pytest.raises(FHIRException) as exc:
        exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe="some-jwe",
            blind_factor="some-oprf-key",
        )

    detail = cast(dict[str, Any], exc.value.detail)
    issue = detail["issue"][0]
    assert exc.value.status_code == 500
    assert issue["code"] == "exception"
    assert issue["details"]["text"] == "Pseudonym could not be exchanged"
    assert issue["expression"] == ["NVIDataReference.subject"]


def test_exchange_oprf_should_return_pseudonym_when_exchange_succeeds() -> None:
    pseudonym_service = MagicMock(spec=PseudonymService)
    expected = Pseudonym("expected-pseudonym")
    pseudonym_service.exchange.return_value = expected

    actual = exchange_oprf(
        pseudonym_service=pseudonym_service,
        oprf_jwe="valid-jwe",
        blind_factor="valid-oprf-key",
    )

    assert actual == expected
