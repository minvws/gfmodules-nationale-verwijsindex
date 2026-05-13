import logging

import inject

from app.config import (
    Config,
    ConfigCryptoServiceApi,
    get_config,
)
from app.db.db import Database
from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.services.auth.header import AuthHeaderService
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
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

    auth_header_service = AuthHeaderService(config=config.oauth)
    binder.bind(AuthHeaderService, auth_header_service)

    crypto_client = create_crypto_service_api_client(config.crypto_service_api)
    binder.bind(CryptoServiceApiClient, crypto_client)

    localization_list_service = LocalizationListService(referral_service, crypto_client)
    binder.bind(LocalizationListService, localization_list_service)

    bundle_service = BundleService(localization_list_service)
    binder.bind(BundleService, bundle_service)

    binder.bind(ConfigCryptoServiceApi, config.crypto_service_api)


def create_crypto_service_api_client(config: ConfigCryptoServiceApi) -> CryptoServiceApiClient:
    if config.enabled:
        return CryptoServiceApiClient(config)
    return CryptoServiceApiClientMock()


def configure() -> None:
    inject.configure(container_config, once=True)
