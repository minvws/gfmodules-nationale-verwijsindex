from pydantic import BaseModel, Field


class DeviceParams(BaseModel):
    org_identifier: str = Field(alias="organization.identifier")
