from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM
from app.models.fhir.resources.organization.parameters import Parameters
from app.routers.organization import localize
from app.services.organization import OrganizationService
from app.services.prs.exception import PseudonymError
from app.services.prs.pseudonym_service import PseudonymService


def _build_localize_parameters() -> Parameters:
    return Parameters.model_validate(
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "invalid-jwe"},
                {"name": "oprfKey", "valueString": "invalid-oprf-key"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "MedicationAgreement",
                    },
                },
            ],
        }
    )


def test_localize_should_raise_400_when_pseudonym_request_is_invalid() -> None:
    parameters = _build_localize_parameters()
    pseudonym_service = MagicMock(spec=PseudonymService)
    organization_service = MagicMock(spec=OrganizationService)
    pseudonym_service.exchange.side_effect = PseudonymError("Invalid pseudonym request")

    with pytest.raises(FHIRException) as exc:
        localize(
            parameters=parameters,
            pseudonym_service=pseudonym_service,
            organization_service=organization_service,
        )

    detail = cast(dict[str, Any], exc.value.detail)
    issue = detail["issue"][0]
    assert exc.value.status_code == 400
    assert issue["code"] == "invalid"
    assert issue["details"]["text"] == "Invalid pseudonym request"
    assert issue["expression"] == ["Parameters.parameter.pseudonym"]
    organization_service.get.assert_not_called()


def test_localize_should_raise_500_when_pseudonym_exchange_fails_unexpectedly() -> None:
    parameters = _build_localize_parameters()
    pseudonym_service = MagicMock(spec=PseudonymService)
    organization_service = MagicMock(spec=OrganizationService)
    pseudonym_service.exchange.side_effect = RuntimeError("unexpected failure")

    with pytest.raises(FHIRException) as exc:
        localize(
            parameters=parameters,
            pseudonym_service=pseudonym_service,
            organization_service=organization_service,
        )

    detail = cast(dict[str, Any], exc.value.detail)
    issue = detail["issue"][0]
    assert exc.value.status_code == 500
    assert issue["code"] == "exception"
    assert issue["details"]["text"] == "Pseudonym could not be exchanged"
    assert issue["expression"] == ["Parameters.parameter.pseudonym"]
    organization_service.get.assert_not_called()
