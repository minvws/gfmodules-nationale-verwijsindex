import logging

import inject

from app.config import (
    Config,
    ConfigOAuthTokenClient,
    ConfigOAuthTokenValidator,
    ConfigPseudonymApi,
    get_config,
)
from app.db.db import Database
from app.models.ura import UraNumber
from app.services.decrypt_service import DecryptService
from app.services.fhir.localization_list import LocalizationListService
from app.services.oauth_token_client import OAuthTokenClient
from app.services.oauth_token_validator import OAuthTokenValidator
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
    binder.bind(OrganizationService, organization_service)

    bind_prs_registration_service(binder, config.pseudonym_api)
    bind_oauth_token_validator(binder, config.oauth_validator)
    bind_oauth_token_client(binder, config.oauth_client)

    pseudonym_service = create_pseudonym_service(config.pseudonym_api)
    binder.bind(PseudonymService, pseudonym_service)

    localization_list_service = LocalizationListService(referral_service, pseudonym_service)
    binder.bind(LocalizationListService, localization_list_service)

    binder.bind(ConfigPseudonymApi, config.pseudonym_api)

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
    oauth_token_client: OAuthTokenClient,
) -> PrsRegistrationService:
    return PrsRegistrationService(
        ura_number=ura_number,
        config=config_pseudonym_api,
        client_oauth_service=oauth_token_client,
    )


def bind_oauth_token_client(
    binder: inject.Binder,
    config_oauth_client: ConfigOAuthTokenClient,
) -> None:
    if config_oauth_client.enabled:
        binder.bind(OAuthTokenClient, OAuthTokenClient(config_oauth_client))
    else:
        from app.debug.oauth_token_client_mock import OAuthTokenClientMock

        binder.bind(OAuthTokenClient, OAuthTokenClientMock())


def bind_oauth_token_validator(
    binder: inject.Binder,
    config_oauth_validator: ConfigOAuthTokenValidator,
) -> None:
    if config_oauth_validator.enabled:
        binder.bind(OAuthTokenValidator, OAuthTokenValidator(config_oauth_validator))
    else:
        from app.debug.oauth_token_validator_mock import OAuthTokenValidatorMock

        binder.bind(
            OAuthTokenValidator,
            OAuthTokenValidatorMock(UraNumber(config_oauth_validator.override_ura_number)),
        )


def create_pseudonym_service(config: ConfigPseudonymApi) -> PseudonymService:
    if config.enabled:
        decryption_service = DecryptService(mtls_key=config.mtls_key)
        return PseudonymService(decryption_service)

    from app.debug.pseudonym_service_mock import PseudonymServiceMock

    return PseudonymServiceMock()


def configure() -> None:
    inject.configure(container_config, once=True)
