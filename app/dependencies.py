import inject

from app.config import Config
from app.db.db import Database
from app.jwt_validator import JwtValidator
from app.services.ca import CaService
from app.services.oauth import OAuthService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService


def get_default_config() -> Config:
    return inject.instance(Config)


def get_database() -> Database:
    return inject.instance(Database)


def get_referral_service() -> ReferralService:
    return inject.instance(ReferralService)  # type: ignore


def get_pseudonym_service() -> PseudonymService:
    return inject.instance(PseudonymService)


def get_prs_registration_service() -> PrsRegistrationService:
    return inject.instance(PrsRegistrationService)


def get_jwt_validator() -> JwtValidator:
    return inject.instance(JwtValidator)


def get_oauth_service() -> OAuthService:
    return inject.instance(OAuthService)


def get_ca_service() -> CaService:
    return inject.instance(CaService)
