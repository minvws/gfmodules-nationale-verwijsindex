import inject
from fastapi import Request

from app.config import Config
from app.data import UraNumber
from app.db.db import Database
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.services.ura_number_finder import (
    StarletteRequestURANumberFinder,
)


def get_default_config() -> Config:
    return inject.instance(Config)


def get_database() -> Database:
    return inject.instance(Database)


def get_referral_service() -> ReferralService:
    return inject.instance(ReferralService)


def get_pseudonym_service() -> PseudonymService:
    return inject.instance(PseudonymService)


def authenticated_ura(request: Request) -> UraNumber:
    finder = inject.instance(StarletteRequestURANumberFinder)

    if not isinstance(finder, StarletteRequestURANumberFinder):
        raise RuntimeError(
            "URA number finder should implement the interface!",
        )
    return finder.find(request)
