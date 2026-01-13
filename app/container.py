import logging
from pathlib import Path

import inject
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Config, read_ini_file
from app.db.db import Database
from app.jwt_validator import JwtValidator
from app.services.client_oauth import ClientOAuthService
from app.services.decrypt_service import DecryptService
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.prs.registration_service import PrsRegistrationService
from app.services.referral_service import ReferralService
from app.utils.certificates.dezi import (
    get_ura_from_cert,
    load_dezi_signing_certificates,
)
from app.utils.certificates.utils import load_certificate

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_INI_FILE = PROJECT_ROOT / "app.conf"


def _load_default_config(config_path: Path) -> Config:
    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    ini_data = read_ini_file(config_path)

    try:
        # Convert database.retry_backoff to a list of floats
        if "retry_backoff" in ini_data["database"] and isinstance(ini_data["database"]["retry_backoff"], str):
            # convert the string to a list of floats
            ini_data["database"]["retry_backoff"] = [float(i) for i in ini_data["database"]["retry_backoff"].split(",")]

        config = Config(**ini_data)
    except ValidationError as e:
        logger.error(f"Configuration validation error: {e}")
        raise e

    return config


def container_config(binder: inject.Binder) -> None:
    config = _load_default_config(DEFAULT_CONFIG_INI_FILE)
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

    # JWT validator for NVI
    ca_certificate = load_certificate(config.dezi_register.uzi_server_certificate_ca_cert_path)
    dezi_signing_certificates = load_dezi_signing_certificates(
        config.dezi_register.dezi_register_trusted_signing_certs_store_path
    )
    jwt_validator = JwtValidator(
        ca_certificate=ca_certificate,
        dezi_register_signing_certificates=dezi_signing_certificates,
    )
    binder.bind(JwtValidator, jwt_validator)

    client_oauth_service = ClientOAuthService(config.client_oauth)
    binder.bind(ClientOAuthService, client_oauth_service)


def configure() -> None:
    inject.configure(container_config, once=True)
