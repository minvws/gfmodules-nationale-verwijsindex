import logging
from pathlib import Path

import inject
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Config, ConfigUraMiddleware, read_ini_file
from app.data import UraNumber
from app.db.db import Database
from app.services.api_service import HttpService
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.lmr_service import LmrService
from app.services.authorization_services.stub import StubAuthService
from app.services.decrypt_service import DecryptService
from app.services.entity.referral_entity_service import ReferralEntityService
from app.services.jwt_validator import JwtValidator
from app.services.pseudonym_service import PseudonymService
from app.ura.ura_middleware.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.ura.ura_middleware.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.ura.ura_middleware.request_ura_middleware import RequestUraMiddleware
from app.ura.ura_middleware.ura_middleware import UraMiddleware

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
        raise e

    return config


def _ura_middleware(config: ConfigUraMiddleware, db: Database) -> UraMiddleware:
    ura_middleware: UraMiddleware
    if config.override_authentication_ura:
        ura_middleware = ConfigBasedUraMiddleware(UraNumber(config.override_authentication_ura))
    else:
        ura_middleware = RequestUraMiddleware()
    if config.use_authentication_ura_allowlist:
        return AllowlistedUraMiddleware(db, ura_middleware, config.allowlist_cache_in_seconds)
    return ura_middleware


def container_config(binder: inject.Binder) -> None:
    config = _load_default_config(DEFAULT_CONFIG_INI_FILE)

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    if config.app.authorization_service:
        lmr_service = LmrService(
            api_service=HttpService(
                base_url="",
                timeout=config.lmr_api.timeout,
                retries=config.lmr_api.retries,
                backoff=config.lmr_api.retry_backoff,
                mtls_cert=config.lmr_api.mtls_cert,
                mtls_key=config.lmr_api.mtls_key,
                mtls_ca=config.lmr_api.mtls_ca,
            )
        )
        # Bind services to different identifiers
        binder.bind(LmrService, lmr_service)
    else:
        stub_service = StubAuthService()
        binder.bind(BaseAuthService, stub_service)

    referral_entity_service = ReferralEntityService(
        database=db,
    )
    binder.bind(ReferralEntityService, referral_entity_service)

    decrypt_service = DecryptService(mtls_key=config.pseudonym_api.mtls_key)
    binder.bind(DecryptService, decrypt_service)

    pseudonym_service = PseudonymService(
        mtls_cert=config.pseudonym_api.mtls_cert,
        decrypt_service=decrypt_service,
        api_service=HttpService(
            base_url=config.pseudonym_api.endpoint,
            timeout=config.pseudonym_api.timeout,
            retries=config.pseudonym_api.retries,
            backoff=config.pseudonym_api.retry_backoff,
            mtls_cert=config.pseudonym_api.mtls_cert,
            mtls_key=config.pseudonym_api.mtls_key,
            mtls_ca=config.pseudonym_api.mtls_ca,
        ),
    )

    binder.bind(PseudonymService, pseudonym_service)

    # JWT validator for NVI
    jwt_validator = JwtValidator(
        uzi_server_certificate_ca_cert_path=config.dezi_register.uzi_server_certificate_ca_cert_path,
        dezi_register_trusted_signing_certs_store_path=config.dezi_register.dezi_register_trusted_signing_certs_store_path,
    )
    binder.bind(JwtValidator, jwt_validator)

    binder.bind(Config, config)
    binder.bind(UraMiddleware, _ura_middleware(config.ura_middleware, db))


def configure() -> None:
    inject.configure(container_config, once=True)
