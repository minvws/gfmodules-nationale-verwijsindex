from typing import Any

import inject

from app.config import Config
from app.db.db import Database
from app.services.auth.header import AuthHeaderService
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
from app.services.referral_service import ReferralService
from app.utils.load_capability_statement import CapabilityStatement


def get_default_config() -> Config:
    return inject.instance(Config)


def get_database() -> Database:
    return inject.instance(Database)


def get_referral_service() -> ReferralService:
    return inject.instance(ReferralService)


def get_crypto_service_api_client() -> CryptoServiceApiClient:
    return inject.instance(CryptoServiceApiClient)


def get_auth_header_service() -> AuthHeaderService:
    return inject.instance(AuthHeaderService)


def get_capability_statement() -> dict[str, Any]:
    return inject.instance(CapabilityStatement)


def get_bundle_service() -> BundleService:
    return inject.instance(BundleService)


def get_localization_list_service() -> LocalizationListService:
    return inject.instance(LocalizationListService)
