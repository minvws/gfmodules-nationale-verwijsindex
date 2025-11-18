import base64
import logging
from pathlib import Path

import inject
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Config, ConfigUraMiddleware, read_ini_file
from app.data import UraNumber
from app.db.db import Database
from app.jwt_validator import DeziSigningCert, JwtValidator
from app.services.authorization_services.authorization_interface import BaseAuthService
from app.services.authorization_services.lmr_service import LmrService
from app.services.authorization_services.stub import StubAuthService
from app.services.decrypt_service import DecryptService
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
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
        logger.error(f"Configuration validation error: {e}")
        raise e

    return config


def _load_certificate(cert_path: str) -> x509.Certificate:
    """Load and parse CA certificate from file path."""
    file_path = Path(cert_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as file:
        cert_data = file.read()
        try:
            return x509.load_pem_x509_certificate(cert_data.encode())
        except Exception as e:
            raise ValueError(f"Failed to parse CA certificate from path {file_path} with error: {e}")


def _load_dezi_signing_certificates(cert_store_path: str) -> list[DeziSigningCert]:
    """
    Load the DEZI signing certificates from the given directory path and return them as a list of DeziSigningCert objects.
    The certificates are expected to be in PEM format.
    """
    if not cert_store_path:
        raise ValueError("DEZI signing certificate path is required")

    dir_path = Path(cert_store_path)
    if not dir_path.exists():
        raise FileNotFoundError(f"DEZI signing certificates not found at: {dir_path}")

    certificates = []
    for cert_file in dir_path.iterdir():
        certificate: x509.Certificate
        try:
            certificate = _load_certificate(str(cert_file))
        except ValueError as e:
            logger.warning(e)
            continue

        # Generate x5t (X.509 certificate SHA-1 thumbprint)
        sha1_fingerprint = certificate.fingerprint(hashes.SHA1())  # NOSONAR
        x5t = base64.urlsafe_b64encode(sha1_fingerprint).decode("utf-8")
        x5t = x5t.rstrip("=")  # Remove padding for x5t

        public_key = certificate.public_key()
        if not isinstance(
            public_key,
            (
                rsa.RSAPublicKey,
                ec.EllipticCurvePublicKey,
                ed25519.Ed25519PublicKey,
                ed448.Ed448PublicKey,
            ),
        ):
            raise TypeError(f"Unsupported public key type in DEZI certificate: {type(public_key)}")

        certificates.append(
            DeziSigningCert(
                certificate=certificate,
                public_key=public_key,
                x5t=x5t,
            )
        )
    return certificates


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
    provider_id = config.app.provider_id

    db = Database(config_database=config.database)
    binder.bind(Database, db)

    auth_service: BaseAuthService
    if config.app.authorization_service:
        auth_service = LmrService(
            mtls_cert=config.lmr_api.mtls_cert,
            mtls_key=config.lmr_api.mtls_key,
            mtls_ca=config.lmr_api.mtls_ca,
        )
    else:
        auth_service = StubAuthService()
    binder.bind(BaseAuthService, auth_service)

    referral_service = ReferralService(database=db, auth_service=auth_service)
    binder.bind(ReferralService, referral_service)

    decrypt_service = DecryptService(mtls_key=config.pseudonym_api.mtls_key)
    binder.bind(DecryptService, decrypt_service)

    pseudonym_service = PseudonymService(
        endpoint=config.pseudonym_api.endpoint,
        timeout=config.pseudonym_api.timeout,
        provider_id=provider_id,
        mtls_cert=config.pseudonym_api.mtls_cert,
        mtls_key=config.pseudonym_api.mtls_key,
        mtls_ca=config.pseudonym_api.mtls_ca,
        decrypt_service=decrypt_service,
    )

    binder.bind(PseudonymService, pseudonym_service)

    # JWT validator for NVI
    ca_certificate = _load_certificate(config.dezi_register.uzi_server_certificate_ca_cert_path)
    dezi_signing_certificates = _load_dezi_signing_certificates(
        config.dezi_register.dezi_register_trusted_signing_certs_store_path
    )
    jwt_validator = JwtValidator(
        ca_certificate=ca_certificate,
        dezi_register_signing_certificates=dezi_signing_certificates,
    )
    binder.bind(JwtValidator, jwt_validator)

    binder.bind(Config, config)
    binder.bind(UraMiddleware, _ura_middleware(config.ura_middleware, db))


def configure() -> None:
    inject.configure(container_config, once=True)
