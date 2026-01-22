import logging

import inject

from app.config import Config, get_config
from app.db.db import Database
from app.services.client_oauth import ClientOAuthService
from app.services.decrypt_service import DecryptService
from app.services.oauth import OAuthService
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.utils.certificates.dezi import (
    get_ura_from_cert,
)
from app.utils.load_capability_statement import CapabilityStatement, load_capability_statement

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

    organization_service = OrganizationService(database=db)
    binder.bind(OrganizationService, organization_service)

    decrypt_service = DecryptService(mtls_key=config.pseudonym_api.mtls_key)
    binder.bind(DecryptService, decrypt_service)

    pseudonym_service = PseudonymService(
        decrypt_service=decrypt_service,
    )
    binder.bind(PseudonymService, pseudonym_service)

    client_oauth_service = ClientOAuthService(
        mock=not config.oauth_outgoing.enabled,
        endpoint=config.oauth_outgoing.endpoint,
        mtls_cert=config.oauth_outgoing.mtls_cert,
        mtls_key=config.oauth_outgoing.mtls_key,
        verify_ca=config.oauth_outgoing.verify_ca,
        timeout=config.oauth_outgoing.timeout,
    )
    binder.bind(ClientOAuthService, client_oauth_service)

    prs_registration_service = PrsRegistrationService(
        get_ura_from_cert(config.pseudonym_api.mtls_cert),
        config.pseudonym_api,
        client_oauth_service,
    )
    binder.bind(PrsRegistrationService, prs_registration_service)

    oauth_service = OAuthService(config.oauth_incoming)
    binder.bind(OAuthService, oauth_service)


def configure() -> None:
    inject.configure(container_config, once=True)
