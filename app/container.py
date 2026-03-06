import logging

import inject

from app.config import (
    Config,
    ConfigClientOAuth,
    ConfigOAuth,
    ConfigPseudonymApi,
    get_config,
)
from app.db.db import Database
from app.debug.pseudonym_service_mock import PseudonymServiceMock
from app.models.ura import UraNumber
from app.services.client_oauth import ClientOAuthService
from app.services.decrypt_service import DecryptService
from app.services.localization_list import LocalizationListService
from app.services.oauth import OAuthService
from app.services.organization import OrganizationService
from app.services.prs.prs_registration_service import PrsRegistrationService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.utils.certificates.dezi import (
    get_ura_from_cert,
)
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

    organization_service = OrganizationService(database=db)

    bind_prs_registration_service(binder, config.pseudonym_api)
    bind_oauth_service(binder, config.oauth)

    pseudonym_service = create_pseudonym_service(config.pseudonym_api)
    bind_pseudonym_service(binder, pseudonym_service)

    localization_list_service = LocalizationListService(referral_service, pseudonym_service)
    binder.bind(LocalizationListService, localization_list_service)

    binder.bind(OrganizationService, organization_service)

    binder.bind(ConfigPseudonymApi, config.pseudonym_api)
    binder.bind(ConfigClientOAuth, config.client_oauth)

    binder.bind_to_provider(DecryptService, lambda: DecryptService(mtls_key=config.pseudonym_api.mtls_key))


def bind_prs_registration_service(binder: inject.Binder, config_pseudonym_api: ConfigPseudonymApi) -> None:
    if config_pseudonym_api.enabled:
        binder.bind_to_provider(
            PrsRegistrationService,
            lambda: create_prs_registration_service(get_ura_from_cert(config_pseudonym_api.mtls_cert)),  # pyright: ignore[reportCallIssue]
        )
    else:
        from app.debug.prs_registration_service import PrsRegistrationServiceMock

        binder.bind_to_constructor(PrsRegistrationService, PrsRegistrationServiceMock)


@inject.autoparams()
def create_prs_registration_service(
    ura_number: UraNumber,
    config_pseudonym_api: ConfigPseudonymApi,
    client_oauth_service: ClientOAuthService,
) -> PrsRegistrationService:
    return PrsRegistrationService(
        ura_number=ura_number,
        config=config_pseudonym_api,
        client_oauth_service=client_oauth_service,
    )


def bind_oauth_service(binder: inject.Binder, config_oauth: ConfigOAuth) -> None:
    if config_oauth.enabled:
        binder.bind(OAuthService, OAuthService)
    else:
        from app.debug.oauth_service_mock import OAuthServiceMock

        binder.bind(OAuthService, OAuthServiceMock(UraNumber(config_oauth.override_ura_number)))


def bind_pseudonym_service(binder: inject.Binder, service: PseudonymService) -> None:
    if isinstance(service, PseudonymServiceMock):
        binder.bind(service, PseudonymServiceMock)
    else:
        binder.bind(service, PseudonymService)


def create_pseudonym_service(config: ConfigPseudonymApi) -> PseudonymService:
    if config.enabled:
        decryption_service = DecryptService(mtls_key=config.mtls_key)
        return PseudonymService(decryption_service)

    return PseudonymServiceMock()


def configure() -> None:
    inject.configure(container_config, once=True)
