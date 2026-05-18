from pydantic import BaseModel


class LocalizeRequest(BaseModel):
    pseudonym: str
    oprf_key: str


class Source(BaseModel):
    ura: str
    source_id: str


class LocalizeResponse(BaseModel):
    results: list[Source]
