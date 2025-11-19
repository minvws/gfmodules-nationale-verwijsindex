import enum


class ReferralRequestType(str, enum.Enum):
    CREATE = "create"
    DELETE = "delete"
    QUERY = "query"
