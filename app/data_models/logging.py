from typing import Any

from pydantic import BaseModel

from app.data import ReferralRequestType
from app.data_models.typing import UraNumber


class ReferralLoggingPayload(BaseModel):
    endpoint: str
    requesting_uzi_number: str
    requesting_ura_number: UraNumber
    request_type: ReferralRequestType
    payload: dict[str, Any]
