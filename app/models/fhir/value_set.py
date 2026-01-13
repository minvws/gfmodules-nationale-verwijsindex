from pydantic import BaseModel


class NviOrganizationTypes(BaseModel):
    code: str
    display: str


class Hcim2024Zibs(BaseModel):
    code: str
    display: str
    definition: str | None = None
