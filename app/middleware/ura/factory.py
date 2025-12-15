from app.config import ConfigUraMiddleware
from app.db.db import Database
from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.middleware.ura.request_ura_middleware import RequestUraMiddleware
from app.middleware.ura.ura_middleware import UraMiddleware
from app.models.ura import UraNumber


def create_ura_middleware(config: ConfigUraMiddleware, db: Database) -> UraMiddleware:
    filter_service = (
        AllowlistedUraMiddleware(db, config.allowlist_cache_in_seconds)
        if config.use_authentication_ura_allowlist
        else None
    )
    if config.override_authentication_ura:
        return ConfigBasedUraMiddleware(
            config_value=UraNumber(config.override_authentication_ura),
            filter_service=filter_service,
        )

    return RequestUraMiddleware(filter_service=filter_service)
