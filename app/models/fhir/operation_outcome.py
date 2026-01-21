from typing import List

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.fhir.elements import Coding


class OperationOutcomeDetail(BaseModel):
    coding: List[Coding] | None = None
    text: str


class OperationOutcomeIssue(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    severity: str
    code: str
    details: OperationOutcomeDetail | None = None
    expression: List[str] | None = None


class OperationOutcome(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: str = "OperationOutcome"
    issue: List[OperationOutcomeIssue]
