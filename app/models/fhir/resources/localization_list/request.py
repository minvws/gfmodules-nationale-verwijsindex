from pydantic import BaseModel, Field

from app.models.fhir.elements import Identifier
from app.models.fhir.resources.data import DEVICE_SYSTEM, PSEUDONYM_SYSTEM


class LocalizationListParams(BaseModel):
    subject: str | None = Field(alias="subject:identifier", default=None)
    code: str | None = Field(default=None)
    source: str | None = Field(alias="source:identifier", default=None)

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
