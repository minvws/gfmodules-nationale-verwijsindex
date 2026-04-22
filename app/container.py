import logging

import inject

from app.config import (
    Config,
    ConfigClientOAuth,
    ConfigPseudonymApi,
    get_config,
)
from app.db.db import Database
from app.models.ura import UraNumber
from app.services.auth.header import AuthHeaderService
from app.services.client_oauth import ClientOAuthService
from app.services.decrypt_service import DecryptService
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
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

    auth_header_service = AuthHeaderService(config=config.oauth)
    binder.bind(AuthHeaderService, auth_header_service)

    bind_prs_registration_service(binder, config.pseudonym_api)

    pseudonym_service = create_pseudonym_service(config.pseudonym_api)
    binder.bind(PseudonymService, pseudonym_service)

    localization_list_service = LocalizationListService(referral_service, pseudonym_service)
    binder.bind(LocalizationListService, localization_list_service)

    bundle_service = BundleService(localization_list_service)
    binder.bind(BundleService, bundle_service)

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


def create_pseudonym_service(config: ConfigPseudonymApi) -> PseudonymService:
    if config.enabled:
        decryption_service = DecryptService(mtls_key=config.mtls_key)
        return PseudonymService(decryption_service)

    from app.debug.pseudonym_service_mock import PseudonymServiceMock

    return PseudonymServiceMock()


def configure() -> None:
    inject.configure(container_config, once=True)
