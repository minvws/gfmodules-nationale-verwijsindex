from typing import List

from pydantic import BaseModel


class Coding(BaseModel):
    system: str
    code: str


class CodeableConcept(BaseModel):
    coding: List[Coding]


class Identifier(BaseModel):
    system: str
    value: str
