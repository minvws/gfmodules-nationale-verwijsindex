from enum import Enum


class AuthorizationScope(str, Enum):
    CREATE = "nvi:create"
    DELETE = "nvi:delete"
    READ = "nvi:read"
    LOCALIZE = "nvi:localize"
