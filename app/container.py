import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.client_oauth import ClientOAuthService
from app.services.decrypt_service import DecryptService
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.utils.certificates.dezi import (
    get_ura_from_cert,
)

logger = logging.getLogger(__name__)


def container_config(binder: inject.Binder) -> None:
    config = get_config()

    binder.bind(Config, config)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    referral_service = ReferralService(database=db)
    binder.bind(ReferralService, referral_service)

    organization_service = OrganizationService(database=db)
    binder.bind(OrganizationService, organization_service)

    decrypt_service = DecryptService(mtls_key=config.pseudonym_api.mtls_key)
    binder.bind(DecryptService, decrypt_service)

    pseudonym_service = PseudonymService(
        decrypt_service=decrypt_service,
    )
    binder.bind(PseudonymService, pseudonym_service)

    prs_registration_service = PrsRegistrationService(
        config=config.pseudonym_api,
        ura_number=get_ura_from_cert(config.pseudonym_api.mtls_cert),
    )
    binder.bind(PrsRegistrationService, prs_registration_service)

    client_oauth_service = ClientOAuthService(config.client_oauth)
    binder.bind(ClientOAuthService, client_oauth_service)


def configure() -> None:
    inject.configure(container_config, once=True)
