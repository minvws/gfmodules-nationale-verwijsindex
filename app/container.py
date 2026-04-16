import logging

import inject

from app.config import (
    Config,
    ConfigClientOAuth,
    ConfigOAuth,
    get_config,
)
from app.db.db import Database
from app.models.ura import UraNumber
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
from app.services.oauth import OAuthService
from app.services.referral_service import ReferralService
from app.utils.load_capability_statement import (
    CapabilityStatement,
    load_capability_statement,
)

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()

    binder.bind(Config, config)

    capability_statement = load_capability_statement()
    binder.bind(CapabilityStatement, capability_statement)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    referral_service = ReferralService(database=db)
    binder.bind(ReferralService, referral_service)

    bind_oauth_service(binder, config.oauth)

    localization_list_service = LocalizationListService(referral_service)
    binder.bind(LocalizationListService, localization_list_service)

    bundle_service = BundleService(localization_list_service)
    binder.bind(BundleService, bundle_service)

    binder.bind(ConfigClientOAuth, config.client_oauth)


def bind_oauth_service(binder: inject.Binder, config_oauth: ConfigOAuth) -> None:
    if config_oauth.enabled:
        binder.bind(OAuthService, OAuthService(config_oauth))
    else:
        from app.debug.oauth_service_mock import OAuthServiceMock

        binder.bind(OAuthService, OAuthServiceMock(UraNumber(config_oauth.override_ura_number)))


def configure() -> None:
    inject.configure(container_config, once=True)
