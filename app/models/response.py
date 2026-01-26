from fastapi import Response
from fastapi.responses import JSONResponse


class FHIRJSONResponse(JSONResponse):
    media_type = "application/fhir+json"


class DeleteResponse(Response):
    media_type = None
    status_code = 204
