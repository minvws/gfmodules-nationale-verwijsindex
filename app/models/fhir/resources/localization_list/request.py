from pydantic import BaseModel, Field

from app.models.fhir.elements import Identifier


class LocalizationListParams(BaseModel):
    patient: str | None = Field(alias="patient.identifier", default=None)
    code: str | None = Field(default=None)
    source: str | None = Field(alias="source.identifier", default=None)

    def get_patient_identifier(self) -> Identifier:
        if self.patient is None:
            raise ValueError("Unable to retrieve required properties for Identifier object, patient value is None")
        return Identifier.from_query(self.patient)

    def get_source_identifier(self) -> Identifier:
        if self.source is None:
            raise ValueError("Unable to retrieve required properties for Identigier object, source value is None")

        return Identifier.from_query(self.source)
