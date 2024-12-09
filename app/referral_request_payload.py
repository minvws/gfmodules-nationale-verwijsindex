from dataclasses import dataclass
from typing import Any

from app.data import UraNumber
from app.referral_request_type import ReferralRequestType


@dataclass
class ReferralLoggingPayload:
    endpoint: str
    requesting_uzi_number: str
    ura_number: UraNumber
    request_type: ReferralRequestType
    payload: dict[str, Any]
