from uuid import UUID

from pydantic import BaseModel


class DomainResource(BaseModel):
    id: UUID | str
