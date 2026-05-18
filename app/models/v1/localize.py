from pydantic import BaseModel


class LocalizeRequest(BaseModel):
    pseudonym: str
    oprf_key: str
    care_context: str | None = None


class Source(BaseModel):
    ura: str
    source_id: str


class LocalizeResponse(BaseModel):
    results: list[Source]
