from pydantic import BaseModel


class Meta(BaseModel):
    limit: int
    offset: int
    total: int
