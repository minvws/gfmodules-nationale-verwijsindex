import logging

from fastapi import Query
from pydantic import BaseModel

from app.models.fhir.elements import Coding, Identifier
from app.models.fhir.resources.data import DATA_DOMAIN_SYSTEM, DEVICE_SYSTEM, PSEUDONYM_SYSTEM
from app.routers.v1.fhir import CODE_PARAM, DEVICE_IDENTIFIER_PARAM, SUBJECT_IDENTIFIER_PARAM

logger = logging.getLogger(__name__)


class LocalizationListParams(BaseModel):
    subject: str | None = Query(alias=SUBJECT_IDENTIFIER_PARAM, example=f"{PSEUDONYM_SYSTEM}|identifier", default=None)
    code: str | None = Query(alias=CODE_PARAM, example=f"{DATA_DOMAIN_SYSTEM}|code", default=None)
    source: str | None = Query(alias=DEVICE_IDENTIFIER_PARAM, example=f"{DEVICE_SYSTEM}|identifier", default=None)

    def get_subject_identifier(self) -> str | None:
        logger.debug(f"Parsing subject identifier from query: {self.subject}")
        if self.subject is None:
            return None
        identifier = Identifier.from_query(query=self.subject, system=PSEUDONYM_SYSTEM)
        logger.debug(f"Parsed subject identifier: system={identifier.system}, value={identifier.value}")
        if not identifier.system or not identifier.value:
            # If system is left out e.g. "|12345" we don't return anything since our identifiers should always have a system: see https://r4.fhir.space/search.html#token
            return None
        return identifier.value

    def get_source_identifier(self) -> str | None:
        logger.debug(f"Parsing source identifier from query: {self.source}")
        if self.source is None:
            return None
        identifier = Identifier.from_query(query=self.source, system=DEVICE_SYSTEM)
        logger.debug(f"Parsed source identifier: system={identifier.system}, value={identifier.value}")
        if not identifier.system or not identifier.value:
            return None
        return identifier.value

    def get_code_value(self) -> str | None:
        logger.debug(f"Parsing code value from query: {self.code}")
        if self.code is None:
            return None
        coding = Coding.from_query(query=self.code, system=DATA_DOMAIN_SYSTEM)
        logger.debug(f"Parsed code value: system={coding.system}, code={coding.code}")
        if not coding.system or not coding.code:
            return None
        return coding.code

    def empty(self) -> bool:
        return self.subject is None and self.code is None and self.source is None

    def is_localize_params(self) -> bool:
        return self.subject is not None and self.code is not None and self.source is None
