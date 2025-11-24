from app.config import ConfigUraMiddleware
from app.db.db import Database
from app.models.ura import UraNumber
from app.ura.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.ura.ura_middleware.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.ura.ura_middleware.request_ura_middleware import RequestUraMiddleware
from app.ura.ura_middleware.ura_middleware import UraMiddleware


def create_ura_middleware(config: ConfigUraMiddleware, db: Database) -> UraMiddleware:
    ura_middleware: UraMiddleware
    if config.override_authentication_ura:
        ura_middleware = ConfigBasedUraMiddleware(UraNumber(config.override_authentication_ura))
    else:
        ura_middleware = RequestUraMiddleware()
    if config.use_authentication_ura_allowlist:
        return AllowlistedUraMiddleware(db, ura_middleware, config.allowlist_cache_in_seconds)
    return ura_middleware
