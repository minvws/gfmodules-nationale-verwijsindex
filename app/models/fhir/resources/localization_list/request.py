import logging
from typing import Any

from fastapi import Query
from pydantic import BaseModel, field_validator

from app.models.fhir.elements import Coding, Identifier
from app.models.fhir.resources.data import DEVICE_SYSTEM, PSEUDONYM_SYSTEM
from app.routers.v1.fhir import CODE_PARAM, DEVICE_IDENTIFIER_PARAM, SUBJECT_IDENTIFIER_PARAM

logger = logging.getLogger(__name__)


def _create_openapi_examples(system: str) -> dict[str, Any]:
    return {
        "[code]": {
            "value": "[code]",
            "description": "the value of [code] matches a Coding.code or Identifier.value irrespective of the value of the system property",
        },
        "[system]|[code]": {
            "value": f"{system}|[code]",
            "description": "the value of [code] matches a Coding.code or Identifier.value, and the value of [system] matches the system property of the Identifier or Coding",
        },
        "|[code]": {
            "value": "|[code]",
            "description": "the value of [code] matches a Coding.code or Identifier.value, and the Coding/Identifier has no system property (supported action but not applicable in our implementation since all our identifiers have a system, will not return any results)",
        },
        "[system]|": {
            "value": f"{system}|",
            "description": "any element where the value of [system] matches the system property of the Identifier or Coding (supported action but not applicable in our implementation since all our identifiers have a system, functions identically to leaving the field blank)",
        },
    }


class LocalizationListParams(BaseModel):
    model_config = {"extra": "forbid"}

    subject: str | None = Query(
        alias=SUBJECT_IDENTIFIER_PARAM, openapi_examples=_create_openapi_examples(PSEUDONYM_SYSTEM), default=None
    )
    source: str | None = Query(
        alias=DEVICE_IDENTIFIER_PARAM, openapi_examples=_create_openapi_examples(DEVICE_SYSTEM), default=None
    )

    @field_validator("subject", mode="before")
    @classmethod
    def validate_subject(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            identifier = Identifier.from_query(query=value, system=PSEUDONYM_SYSTEM)
            logger.debug("Validated subject identifier: %r", identifier)
        except ValueError as e:
            raise ValueError(f"Invalid subject identifier: {e}")
        if not identifier.system or not identifier.value:
            # If system is left out e.g. "|12345" we don't return anything since our identifiers should always have a system: see https://r4.fhir.space/search.html#token
            return None
        return identifier.value

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            identifier = Identifier.from_query(query=value, system=DEVICE_SYSTEM)
            logger.debug("Validated source identifier: %r", identifier)
        except ValueError as e:
            raise ValueError(f"Invalid source identifier: {e}")
        if not identifier.system or not identifier.value:
            return None
        return identifier.value

    def empty(self) -> bool:
        return self.subject is None and self.source is None

    def is_localize_params(self) -> bool:
        return self.subject is not None and self.source is None
