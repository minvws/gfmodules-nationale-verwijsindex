from pathlib import Path

import inject
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Config, ConfigUraMiddleware, read_ini_file
from app.data import UraNumber
from app.db.db import Database
from app.middleware.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura_middleware.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.middleware.ura_middleware.request_ura_middleware import RequestUraMiddleware
from app.middleware.ura_middleware.ura_middleware import UraMiddleware
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.stub import StubAuthService
from app.services.authorization_services.toestemming_stub_service import ToestemmingStubService
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

DEFAULT_CONFIG_INI_FILE = PROJECT_ROOT / "app.conf"


def _load_default_config(path: Path) -> Config:
    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    ini_data = read_ini_file(path)

    try:
        # Convert database.retry_backoff to a list of floats
        if "retry_backoff" in ini_data["database"] and isinstance(ini_data["database"]["retry_backoff"], str):
            # convert the string to a list of floats
            ini_data["database"]["retry_backoff"] = [float(i) for i in ini_data["database"]["retry_backoff"].split(",")]

        config = Config(**ini_data)
    except ValidationError as e:
        raise e

    return config


def _ura_middleware(config: ConfigUraMiddleware, db: Database) -> UraMiddleware:
    ura_middleware: UraMiddleware
    if config.override_authentication_ura:
        ura_middleware = ConfigBasedUraMiddleware(UraNumber(config.override_authentication_ura))
    else:
        ura_middleware = RequestUraMiddleware()
    if config.use_authentication_ura_allowlist:
        return AllowlistedUraMiddleware(db, ura_middleware, config.allowlist_cache_in_seconds)
    return ura_middleware


def container_config(binder: inject.Binder) -> None:
    config = _load_default_config(DEFAULT_CONFIG_INI_FILE)
    provider_id = config.app.provider_id

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    if config.app.authorization_service:
        toestemming_stub_service = ToestemmingStubService(
            endpoint=config.toestemming_stub_api.endpoint,
            timeout=config.toestemming_stub_api.timeout,
        )
        # Bind services to different identifiers
        binder.bind(ToestemmingStubService, toestemming_stub_service)

        referral_service = ReferralService(
            database=db,
            toestemming_service=toestemming_stub_service,
        )
        binder.bind(ReferralService, referral_service)
    else:
        stub_service = StubAuthService()
        binder.bind(BaseAuthService, stub_service)

        referral_service = ReferralService(
            database=db,
            toestemming_service=stub_service,
        )
        binder.bind(ReferralService, referral_service)

    pseudonym_service = PseudonymService(
        endpoint=config.pseudonym_api.endpoint,
        timeout=config.pseudonym_api.timeout,
        provider_id=provider_id,
        mtls_cert=config.pseudonym_api.mtls_cert,
        mtls_key=config.pseudonym_api.mtls_key,
        mtls_ca=config.pseudonym_api.mtls_ca,
    )

    binder.bind(PseudonymService, pseudonym_service)
    binder.bind(Config, config)
    binder.bind(UraMiddleware, _ura_middleware(config.ura_middleware, db))


def configure() -> None:
    inject.configure(container_config, once=True)
