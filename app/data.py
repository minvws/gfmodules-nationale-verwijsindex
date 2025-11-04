from enum import Enum


class ReferralRequestType(Enum):
    CREATE = "create"
    DELETE = "delete"
    QUERY = "query"
    TIMELINE_REFERRAL_QUERY = "timeline_referral_query"
