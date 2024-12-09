from pathlib import Path

import inject
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Config, ConfigApp, read_ini_file
from app.db.db import Database
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.services.ura_number_finder import (
    ConfigOverridenMockURANumberFinder,
    RequestURANumberFinder,
    StarletteRequestURANumberFinder,
)

DEFAULT_CONFIG_INI_FILE = PROJECT_ROOT / "app.conf"


def _load_default_config(path: Path) -> Config:
    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    ini_data = read_ini_file(path)

    try:
        # Convert database.retry_backoff to a list of floats
        if "retry_backoff" in ini_data["database"] and isinstance(
            ini_data["database"]["retry_backoff"], str
        ):
            # convert the string to a list of floats
            ini_data["database"]["retry_backoff"] = [
                float(i) for i in ini_data["database"]["retry_backoff"].split(",")
            ]

        config = Config(**ini_data)
    except ValidationError as e:
        raise e

    return config


def _resolve_ura_number_finder(config: ConfigApp) -> StarletteRequestURANumberFinder:
    if config.override_authentication_ura:
        return ConfigOverridenMockURANumberFinder(config.override_authentication_ura)

    return RequestURANumberFinder()


def container_config(binder: inject.Binder) -> None:
    config = _load_default_config(DEFAULT_CONFIG_INI_FILE)
    provider_id = config.app.provider_id

    db = Database(dsn=config.database.dsn, config=config)
    binder.bind(Database, db)

    referral_service = ReferralService(database=db)
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
    binder.bind(StarletteRequestURANumberFinder, _resolve_ura_number_finder(config.app))


def configure() -> None:
    inject.configure(container_config, once=True)
