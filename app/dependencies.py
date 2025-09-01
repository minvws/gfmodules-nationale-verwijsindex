from typing import cast

import inject
from fastapi import Request

from app.config import Config
from app.data import UraNumber
from app.db.db import Database
from app.jwt_validator import JwtValidator
from app.middleware.ura_middleware.ura_middleware import UraMiddleware
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService


def get_default_config() -> Config:
    return inject.instance(Config)


def get_database() -> Database:
    return inject.instance(Database)


def get_referral_service() -> ReferralService:
    return inject.instance(ReferralService)  # type: ignore


def get_pseudonym_service() -> PseudonymService:
    return inject.instance(PseudonymService)


def get_ura_middleware() -> UraMiddleware:
    return cast(UraMiddleware, inject.instance(UraMiddleware))


def get_jwt_validator() -> JwtValidator:
    return inject.instance(JwtValidator)


def authenticated_ura(request: Request) -> UraNumber:
    return get_ura_middleware().authenticated_ura(request)
