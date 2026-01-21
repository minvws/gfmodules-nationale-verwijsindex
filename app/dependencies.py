from typing import Any

import inject

from app.config import Config
from app.db.db import Database
from app.services.oauth import OAuthService
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.utils.load_capability_statement import CapabilityStatement


def get_default_config() -> Config:
    return inject.instance(Config)


def get_database() -> Database:
    return inject.instance(Database)


def get_referral_service() -> ReferralService:
    return inject.instance(ReferralService)  # type: ignore


def get_organization_service() -> OrganizationService:
    return inject.instance(OrganizationService)


def get_pseudonym_service() -> PseudonymService:
    return inject.instance(PseudonymService)


def get_prs_registration_service() -> PrsRegistrationService:
    return inject.instance(PrsRegistrationService)


def get_oauth_service() -> OAuthService:
    return inject.instance(OAuthService)


def get_capability_statement() -> dict[str, Any]:
    return inject.instance(CapabilityStatement)
