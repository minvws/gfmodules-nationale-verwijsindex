import enum
from dataclasses import dataclass
from typing import Any

from app.data import UraNumber


class ReferralRequestType(enum.Enum):
    CREATE = "create"
    DELETE = "delete"
    QUERY = "query"
    TIMELINE_REFERRAL_QUERY = "timeline_referral_query"


@dataclass
class ReferralLoggingPayload:
    endpoint: str
    requesting_uzi_number: str
    requesting_ura_number: UraNumber
    request_type: ReferralRequestType
    payload: dict[str, Any]
