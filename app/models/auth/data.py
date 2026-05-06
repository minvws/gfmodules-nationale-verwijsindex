from enum import Enum


class AuthorizationRole(Enum):
    CONSULTING = "consulting"
    SOURCE = "source"


class AuthorizationScope(str, Enum):
    CREATE = "nvi:create"
    DELETE = "nvi:delete"
    READ = "nvi:read"
    LOCALIZE = "nvi:localize"


class RequestedAction(Enum):
    LOCALIZING = "localizing"
    MANAGING = "managing"
