from fastapi import Query
from pydantic import BaseModel

from app.models.fhir.elements import Identifier
from app.models.fhir.resources.data import DATA_DOMAIN_SYSTEM, DEVICE_SYSTEM, PSEUDONYM_SYSTEM, SUBJECT_SYSTEM
from app.routers.v1.fhir import CODE_PARAM, DEVICE_IDENTIFIER_PARAM, SUBJECT_IDENTIFIER_PARAM


class LocalizationListParams(BaseModel):
    subject: str | None = Query(alias=SUBJECT_IDENTIFIER_PARAM, example=f"{SUBJECT_SYSTEM}|identifier", default=None)
    code: str | None = Query(alias=CODE_PARAM, example=f"{DATA_DOMAIN_SYSTEM}|code", default=None)
    source: str | None = Query(alias=DEVICE_IDENTIFIER_PARAM, example=f"{DEVICE_SYSTEM}|identifier", default=None)

    def get_subject_identifier(self) -> Identifier:
        if self.subject is None:
            raise ValueError("Unable to retrieve required properties for Identifier object, subject value is None")
        return Identifier.from_query(query=self.subject, system=PSEUDONYM_SYSTEM)

    def get_source_identifier(self) -> Identifier:
        if self.source is None:
            raise ValueError("Unable to retrieve required properties for Identifier object, source value is None")

        return Identifier.from_query(query=self.source, system=DEVICE_SYSTEM)

    def empty(self) -> bool:
        return self.subject is None and self.code is None and self.source is None

    def is_localize_params(self) -> bool:
        return self.subject is not None and self.code is not None and self.source is None
