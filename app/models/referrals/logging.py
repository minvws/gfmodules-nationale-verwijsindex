from dataclasses import dataclass
from typing import Any

from app.data import ReferralRequestType
from app.models.ura import UraNumber


@dataclass
class ReferralLoggingPayload:
    endpoint: str
    requesting_uzi_number: str
    ura_number: UraNumber
    request_type: ReferralRequestType
    payload: dict[str, Any]
