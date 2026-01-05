import base64
import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import certifi
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import Certificate
from fastapi import HTTPException, Request
from OpenSSL import crypto

from app.config import ConfigOAuth
from app.db.db import Database
from app.db.models.oauth_token import OAuthTokenEntity
from app.db.repository.oauth_repository import OAuthRepository
from app.models.ura import UraNumber

SSL_CLIENT_CERT_HEADER_NAME = "x-proxy-ssl_client_cert"
SSL_CLIENT_VERIFY_HEADER_NAME = "x-proxy-ssl_client_verify"

CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

logger = logging.getLogger(__name__)


class OAuthInvalidClientError(Exception):
    """
    Raised when the OAuth2 client authentication fails.
    """

    pass


class OAuthInvalidRequestError(Exception):
    """
    Raised when the OAuth2 request is invalid.
    """

    pass


class OAuthError(Exception):
    """
    Raised for general OAuth2 errors.
    """

    def __init__(self, code: str, description: str, status_code: int = 400):
        super().__init__(description)
        self.code = code
        self.description = description
        self.status_code = status_code


class OAuthService:
    def __init__(self, database: Database, oauth_config: ConfigOAuth) -> None:
        self.oauth_config = oauth_config
        self.database = database

    @staticmethod
    def _validate_globals(grant_type: str, scope: Optional[str]) -> None:
        """
        Validate global OAuth2 parameters.
        """

        # Check grant type
        if grant_type != "client_credentials":
            logger.debug("Unsupported grant type: %s", grant_type)
            raise OAuthError("unsupported_grant_type", "Only client_credentials grant type is supported.")
        logger.debug("Requested grant_type: %s", grant_type)

        # Check scope
        if scope not in [None, "read"]:
            logger.debug("Unsupported scope requested: %s", scope)
            raise OAuthError("invalid_scope", "Unsupported scope requested.")
        logger.debug("Requested scope: %s", scope or "read")

    def _validate_client_assertion(
        self, client_assertion_type: Optional[str], client_assertion: Optional[str], request: Request
    ) -> Certificate:
        """
        Validate the client assertion JWT and its certificate chain.
        """

        # Fetch mTLS fingerprint from the request
        mtls_fp = get_mtls_fingerprint_s256(request)
        if not mtls_fp:
            logger.debug("mTLS certificate fingerprint missing")
            raise OAuthInvalidClientError("mTLS certificate fingerprint missing (check proxy mTLS config)")
        logger.debug("mTLS certificate fingerprint (S256): %s", mtls_fp)

        # Make sure assertion type is ok
        if client_assertion_type != CLIENT_ASSERTION_TYPE:
            logger.debug("Unsupported client_assertion_type: %s", client_assertion_type)
            raise OAuthInvalidClientError("client_assertion_type missing or unsupported")
        logger.debug("client_assertion_type: %s", client_assertion_type)

        if not client_assertion or client_assertion.count(".") != 2:
            logger.debug("Invalid or missing client_assertion")
            raise OAuthInvalidClientError("client_assertion missing or not a JWT")
        logger.debug("client_assertion received")

        try:
            return verify_chain_from_x5c(client_assertion, ca_bundle_path=self.oauth_config.ca_cert)
        except Exception:
            logger.debug("Untrusted certificate chain in x5c header")
            raise OAuthInvalidClientError("client_assertion x5c certificate chain is untrusted")

    @staticmethod
    def _validate_claims(cert: Certificate, request: Request, client_assertion: str) -> Any:
        """
        Validate the JWT claims in the client assertion.
        """

        # The token URL is the full URL of this request. The JWT MUST have this as its audience (aud)
        token_url = str(request.url)
        x5c_pub_key = cert.public_key()

        try:
            claims = jwt.decode(
                client_assertion,
                key=x5c_pub_key,  # type: ignore[arg-type]
                algorithms=["RS256"],
                audience=token_url,
                options={
                    "require": ["exp", "iat", "aud"],
                },
            )
        except jwt.ExpiredSignatureError:
            raise OAuthInvalidClientError("client_assertion expired")
        except jwt.InvalidAudienceError:
            raise OAuthInvalidClientError("client_assertion aud mismatch")
        except jwt.InvalidSignatureError:
            raise OAuthInvalidClientError("client_assertion signature invalid")
        except Exception as e:
            raise OAuthInvalidClientError(f"client_assertion invalid: {e}")

        logger.debug("Decoded JWT claims: %s", claims)
        return claims

    @staticmethod
    def _validate_issuer(claims: Any) -> None:
        """
        Validate the issuer and subject claims in the JWT.
        """
        # Check expiry and jti for replay protection
        jti = claims.get("jti")
        exp = claims.get("exp")
        if not isinstance(jti, str) or not jti:
            logger.debug("Missing or invalid jti in client_assertion")
            raise OAuthInvalidClientError("client_assertion jti required")

        if not isinstance(exp, int):
            logger.debug("Missing or invalid exp in client_assertion")
            raise OAuthInvalidClientError("client_assertion exp required")

        # Make sure that the JTI has not been seen before (replay protection)
        if not mark_jti_or_reject(jti, exp):
            logger.debug("Reused jti detected in client_assertion: %s", jti)
            raise OAuthInvalidClientError("client_assertion replay detected (jti reused)")

    @staticmethod
    def _validate_fingerprint(claims: Any, request: Request) -> None:
        """
        Check if cnf.x5t#S256 matches mTLS cert fingerprint
        """
        jwt_fp = extract_cnf_fingerprint(claims)
        mtls_fp = get_mtls_fingerprint_s256(request)
        logger.debug("mTLS fingerprint: %s", mtls_fp)
        logger.debug("JWT provided fingerprint: %s", jwt_fp)

        if not jwt_fp:
            raise OAuthInvalidClientError("client_assertion missing cnf.x5t#S256")

        if jwt_fp != mtls_fp:
            logger.debug("Fingerprint of the mTlS certificate does not match cnf in JWT")
            raise OAuthInvalidClientError("client_assertion cnf fingerprint does not match mTLS certificate")

    def validate(
        self,
        grant_type: str,
        scope: Optional[str],
        client_assertion_type: Optional[str],
        client_assertion: Optional[str],
        request: Request,
    ) -> Any:
        """
        Validate the OAuth2 client credentials request with mTLS and JWT client assertion.
        """

        self._validate_globals(grant_type, scope)
        cert = self._validate_client_assertion(client_assertion_type, client_assertion, request)
        claims = self._validate_claims(cert, request, client_assertion or "")
        self._validate_issuer(claims)
        self._validate_fingerprint(claims, request)

        return claims

    def generate_token(self, ura_number: UraNumber, scopes: List[str]) -> str:
        """
        Generate an OAuth2 token entity and return its access token
        """
        access_token = f"nvi_tok_v1_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)

        entity = OAuthTokenEntity(
            ura_number=str(ura_number),
            token_sha256=hashlib.sha256(access_token.encode("utf-8")).hexdigest(),
            scopes=" ".join(scopes),
            expires_at=now + timedelta(seconds=self.oauth_config.token_lifetime_seconds),
            created_at=now,
        )

        with self.database.get_db_session() as session:
            repo = session.get_repository(OAuthRepository)
            repo.add_one(entity)

        return access_token

    def revoke(self, token_sha256: str) -> None:
        """
        Revoke an OAuth2 token by its SHA-256 hash.
        """
        with self.database.get_db_session() as session:
            repo = session.get_repository(OAuthRepository)
            entity = repo.get_by_token_sha256(token_sha256)

            if not entity:
                raise HTTPException(status_code=404, detail="Token not found")

            entity.revoked = True
            repo.update_one(entity)

    def verify(self, request: Request) -> OAuthTokenEntity:
        """
        Verify an incoming OAuth2 token from the Authorization header.
        """
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

        token = auth_header[7:]  # Remove "Bearer "

        token_sha256 = hashlib.sha256(token.encode("utf-8")).hexdigest()

        with self.database.get_db_session() as session:
            repo = session.get_repository(OAuthRepository)
            entity = repo.get_by_token_sha256(token_sha256)

            if not entity:
                raise HTTPException(status_code=401, detail="Invalid token")

            if entity.revoked:
                raise HTTPException(status_code=401, detail="Token revoked")

            if entity.expires_at < datetime.now(timezone.utc):  # type: ignore[operator]
                raise HTTPException(status_code=401, detail="Token expired")

        return entity


def _b64decode_no_padding(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.b64decode(data + pad)


def generate_fingerprint(cert_bytes: bytes) -> str:
    """
    Generate the SHA-256 fingerprint (base64url-encoded, no padding) of a PEM-encoded certificate.
    """
    cert = x509.load_pem_x509_certificate(cert_bytes)
    der = cert.public_bytes(serialization.Encoding.DER)
    digest = hashlib.sha256(der).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def get_mtls_fingerprint_s256(request: Request) -> Optional[str]:
    """
    Extract the mTLS certificate from the request headers and generate its SHA-256 fingerprint.
    """

    # We extract the mTLS cert
    if SSL_CLIENT_CERT_HEADER_NAME not in request.headers:
        raise HTTPException(
            status_code=401,
            detail="Missing client certificate",
        )
    if SSL_CLIENT_VERIFY_HEADER_NAME not in request.headers:
        raise HTTPException(
            status_code=401,
            detail="Missing client certificate verification header",
        )

    # Sanity check. Apache should not proxy anything that is not verified successfully
    if request.headers[SSL_CLIENT_VERIFY_HEADER_NAME] != "SUCCESS":
        raise HTTPException(
            status_code=401,
            detail="Client certificate verification failed",
        )

    cert = request.headers[SSL_CLIENT_CERT_HEADER_NAME]
    return generate_fingerprint(cert.encode("ascii"))


def _load_openssl_x509_from_der(der: bytes) -> crypto.X509:
    # _load_openssl_x509_from_der()
    return crypto.load_certificate(crypto.FILETYPE_ASN1, der)


def verify_chain_from_x5c(token: str, *, ca_bundle_path: str | None = None) -> x509.Certificate:
    # verify_chain_from_x5c()
    header = jwt.get_unverified_header(token)
    x5c_list = header.get("x5c")
    if not x5c_list or not isinstance(x5c_list, list):
        raise ValueError("JWT header has no x5c chain")

    ders = [_b64decode_no_padding(c) for c in x5c_list]
    openssl_certs = [_load_openssl_x509_from_der(d) for d in ders]

    leaf = openssl_certs[0]
    intermediates = openssl_certs[1:] if len(openssl_certs) > 1 else None

    store = crypto.X509Store()
    store.load_locations(cafile=ca_bundle_path or certifi.where())

    # Verify leaf (and intermediates if provided) against the trust store
    ctx = crypto.X509StoreContext(store, leaf, intermediates)
    ctx.verify_certificate()  # raises on failure

    # Return the leaf cert as a cryptography object too
    leaf_crypto = x509.load_der_x509_certificate(ders[0])
    return leaf_crypto


def extract_cnf_fingerprint(assertion_claims: Dict[str, Any]) -> Optional[str]:
    """
    Extract the cnf.x5t#S256 fingerprint from the JWT claims.
    """
    cnf = assertion_claims.get("cnf")
    if isinstance(cnf, dict):
        fp = cnf.get("x5t#S256")
        if isinstance(fp, str) and fp:
            return fp
    return None


# ----------------------------------------------------------------
# WE should use redis instead.
_seen_jti: Dict[str, int] = {}  # jti -> exp


def _cleanup_seen_jti(now: int) -> None:
    for jti, exp in list(_seen_jti.items()):
        if exp <= now:
            _seen_jti.pop(jti, None)


def mark_jti_or_reject(jti: str, exp: int) -> bool:
    now = int(time.time())
    _cleanup_seen_jti(now)

    if jti in _seen_jti:
        return False

    _seen_jti[jti] = exp
    return True
