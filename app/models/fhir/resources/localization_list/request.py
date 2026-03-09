from pydantic import BaseModel, Field

from app.models.fhir.elements import Identifier
from app.models.fhir.resources.data import DEVICE_SYSTEM, PSEUDONYM_SYSTEM


class LocalizationListParams(BaseModel):
    patient: str | None = Field(alias="patient.identifier", default=None)
    code: str | None = Field(default=None)
    source: str | None = Field(alias="source.identifier", default=None)

    def get_patient_identifier(self) -> Identifier:
        if self.patient is None:
            raise ValueError("Unable to retrieve required properties for Identifier object, patient value is None")
        return Identifier.from_query(query=self.patient, system=PSEUDONYM_SYSTEM)

    def get_source_identifier(self) -> Identifier:
        if self.source is None:
            raise ValueError("Unable to retrieve required properties for Identigier object, source value is None")

        return Identifier.from_query(query=self.source, system=DEVICE_SYSTEM)

    def empty(self) -> bool:
        return self.patient is None and self.code is None and self.source is None
