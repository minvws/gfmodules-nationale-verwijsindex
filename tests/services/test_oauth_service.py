import base64
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import Certificate
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from starlette.requests import Request

from app.config import ConfigOAuth
from app.db.db import Database
from app.db.models.oauth_token import OAuthTokenEntity
from app.models.ura import UraNumber
from app.services.oauth import (
    CLIENT_ASSERTION_TYPE,
    SSL_CLIENT_CERT_HEADER_NAME,
    SSL_CLIENT_VERIFY_HEADER_NAME,
    OAuthError,
    OAuthInvalidClientError,
    OAuthService,
    extract_cnf_fingerprint,
    generate_fingerprint,
    get_mtls_fingerprint_s256,
    mark_jti_or_reject,
    verify_chain_from_x5c,
)


class FakeOAuthRepo:
    def __init__(self) -> None:
        self.added: list[OAuthTokenEntity] = []
        self.by_sha: dict[str, OAuthTokenEntity] = {}

    def add_one(self, entity: OAuthTokenEntity) -> None:
        self.added.append(entity)
        self.by_sha[getattr(entity, "token_sha256")] = entity

    def get_by_token_sha256(self, token_sha256: str) -> OAuthTokenEntity | None:
        return self.by_sha.get(token_sha256)


class FakeSession:
    def __init__(self, repo: FakeOAuthRepo):
        self._repo = repo

    def get_repository(self, repo_cls):
        return self._repo

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeDatabase:
    def __init__(self, repo: FakeOAuthRepo):
        self._repo = repo

    def get_db_session(self):
        return FakeSession(self._repo)


@dataclass
class FakeConfigOAuth:
    ca_cert: str
    token_lifetime_seconds: int = 60


def _make_ca_cert() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test CA Org"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
        ]
    )
    now = datetime.now(timezone.utc)

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    return ca_key, ca_cert


def _make_leaf_cert(ca_key: Any, ca_cert: Certificate) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Leaf Org"),
            x509.NameAttribute(NameOID.COMMON_NAME, "leaf.example"),
        ]
    )
    now = datetime.now(timezone.utc)

    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    return leaf_key, leaf_cert


def _x5c_list_from_certs(*certs: x509.Certificate) -> list[str]:
    out = []
    for c in certs:
        der = c.public_bytes(serialization.Encoding.DER)
        out.append(base64.b64encode(der).decode("ascii"))
    return out


def _make_request(url: str, headers: dict[str, str]) -> Request:
    assert url.startswith("http")
    scheme, rest = url.split("://", 1)
    host, path = rest.split("/", 1)
    if ":" in host:
        server_host, server_port = host.split(":", 1)
        server = (server_host, int(server_port))
    else:
        server = (host, 443 if scheme == "https" else 80)

    raw_headers = [(k.lower().encode(), str(v).encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "scheme": scheme,
        "server": server,
        "path": "/" + path,
        "query_string": b"",
        "headers": raw_headers,
        "method": "POST",
    }
    return Request(scope)


@pytest.fixture()
def ca_and_leaf(tmp_path):
    ca_key, ca_cert = _make_ca_cert()
    leaf_key, leaf_cert = _make_leaf_cert(ca_key, ca_cert)

    ca_pem = ca_cert.public_bytes(serialization.Encoding.PEM)
    ca_path = tmp_path / "test_ca.pem"
    ca_path.write_bytes(ca_pem)

    leaf_pem = leaf_cert.public_bytes(serialization.Encoding.PEM)

    return {
        "ca_key": ca_key,
        "ca_cert": ca_cert,
        "ca_path": str(ca_path),
        "leaf_key": leaf_key,
        "leaf_cert": leaf_cert,
        "leaf_pem": leaf_pem,
    }


@pytest.fixture()
def oauth_service(ca_and_leaf):
    repo = FakeOAuthRepo()
    db = FakeDatabase(repo)
    cfg = FakeConfigOAuth(ca_cert=ca_and_leaf["ca_path"], token_lifetime_seconds=60)
    svc = OAuthService(database=cast(Database, db), oauth_config=cast(ConfigOAuth, cfg))
    return svc, repo, cfg


def test_generate_fingerprint_is_base64url_no_padding(ca_and_leaf):
    fp = generate_fingerprint(ca_and_leaf["leaf_pem"])
    assert isinstance(fp, str)
    assert "=" not in fp  # no padding
    assert all(ch.isalnum() or ch in "-_" for ch in fp)


def test_get_mtls_fingerprint_s256_requires_headers(ca_and_leaf):
    req = _make_request("https://testserver/token", {SSL_CLIENT_VERIFY_HEADER_NAME: "SUCCESS"})
    with pytest.raises(HTTPException) as e:
        get_mtls_fingerprint_s256(req)
    assert e.value.status_code == 401

    # missing verify header
    req = _make_request(
        "https://testserver/token", {SSL_CLIENT_CERT_HEADER_NAME: ca_and_leaf["leaf_pem"].decode("ascii")}
    )
    with pytest.raises(HTTPException) as e:
        get_mtls_fingerprint_s256(req)
    assert e.value.status_code == 401

    # verify not SUCCESS
    req = _make_request(
        "https://testserver/token",
        {
            SSL_CLIENT_CERT_HEADER_NAME: ca_and_leaf["leaf_pem"].decode("ascii"),
            SSL_CLIENT_VERIFY_HEADER_NAME: "FAIL",
        },
    )
    with pytest.raises(HTTPException) as e:
        get_mtls_fingerprint_s256(req)
    assert e.value.status_code == 401


def test_verify_chain_from_x5c_accepts_valid_chain(ca_and_leaf):
    x5c = _x5c_list_from_certs(ca_and_leaf["leaf_cert"], ca_and_leaf["ca_cert"])
    token = jwt.encode(
        {"some": "payload"},
        key="not_used_for_chain_check",
        algorithm="HS256",
        headers={"x5c": x5c},
    )

    leaf = verify_chain_from_x5c(token, ca_bundle_path=ca_and_leaf["ca_path"])
    assert isinstance(leaf, x509.Certificate)
    assert leaf.subject == ca_and_leaf["leaf_cert"].subject


def test_extract_cnf_fingerprint():
    assert extract_cnf_fingerprint({"cnf": {"x5t#S256": "abc"}}) == "abc"
    assert extract_cnf_fingerprint({"cnf": {}}) is None
    assert extract_cnf_fingerprint({}) is None


def test_mark_jti_or_reject_replay_protection(monkeypatch):
    now = int(time.time())
    exp = now + 10

    assert mark_jti_or_reject("jti-1", exp) is True
    assert mark_jti_or_reject("jti-1", exp) is False  # replay

    # after expiry, it should clean up and allow again
    monkeypatch.setattr(time, "time", lambda: float(exp + 1))
    assert mark_jti_or_reject("jti-1", exp + 20) is True


def test_validate_globals_rejects_wrong_grant():
    with pytest.raises(OAuthError) as e:
        OAuthService._validate_globals("authorization_code", None)
    assert e.value.code == "unsupported_grant_type"


def test_validate_globals_rejects_scope():
    with pytest.raises(OAuthError) as e:
        OAuthService._validate_globals("client_credentials", "write")
    assert e.value.code == "invalid_scope"


def test_validate_success_flow(oauth_service, ca_and_leaf):
    svc, _repo, _cfg = oauth_service
    ura_number = UraNumber("12345678")

    # Build request with mTLS headers
    mtls_fp = generate_fingerprint(ca_and_leaf["leaf_pem"])
    req = _make_request(
        "https://testserver/token",
        {
            SSL_CLIENT_CERT_HEADER_NAME: ca_and_leaf["leaf_pem"].decode("ascii"),
            SSL_CLIENT_VERIFY_HEADER_NAME: "SUCCESS",
        },
    )

    # Build JWT client assertion signed with leaf key + x5c chain (leaf + CA)
    now = datetime.now(timezone.utc)
    claims = {
        "iss": f"ura:{ura_number}",
        "sub": f"ura:{ura_number}",
        "aud": str(req.url),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "jti": "unique-jti-123",
        "cnf": {"x5t#S256": mtls_fp},
    }
    x5c = _x5c_list_from_certs(ca_and_leaf["leaf_cert"], ca_and_leaf["ca_cert"])
    assertion = jwt.encode(
        claims,
        key=ca_and_leaf["leaf_key"],
        algorithm="RS256",
        headers={"x5c": x5c},
    )

    svc.validate(
        grant_type="client_credentials",
        scope="read",
        client_assertion_type=CLIENT_ASSERTION_TYPE,
        client_assertion=assertion,
        request=req,
    )


def test_validate_rejects_fingerprint_mismatch(oauth_service, ca_and_leaf):
    svc, _repo, _cfg = oauth_service
    ura_number = UraNumber("12345678")

    req = _make_request(
        "https://testserver/token",
        {
            SSL_CLIENT_CERT_HEADER_NAME: ca_and_leaf["leaf_pem"].decode("ascii"),
            SSL_CLIENT_VERIFY_HEADER_NAME: "SUCCESS",
        },
    )

    now = datetime.now(timezone.utc)
    claims = {
        "iss": f"ura:{ura_number}",
        "sub": f"ura:{ura_number}",
        "aud": str(req.url),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "jti": "unique-jti-xyz",
        "cnf": {"x5t#S256": "WRONG_FP"},
    }
    x5c = _x5c_list_from_certs(ca_and_leaf["leaf_cert"], ca_and_leaf["ca_cert"])
    assertion = jwt.encode(claims, key=ca_and_leaf["leaf_key"], algorithm="RS256", headers={"x5c": x5c})

    with pytest.raises(OAuthInvalidClientError) as e:
        svc.validate(
            grant_type="client_credentials",
            scope="read",
            client_assertion_type=CLIENT_ASSERTION_TYPE,
            client_assertion=assertion,
            request=req,
        )
    assert "cnf fingerprint does not match" in str(e.value)


def test_validate_rejects_audience_mismatch(oauth_service, ca_and_leaf):
    svc, _repo, _cfg = oauth_service
    ura_number = UraNumber("12345678")

    req = _make_request(
        "https://testserver/token",
        {
            SSL_CLIENT_CERT_HEADER_NAME: ca_and_leaf["leaf_pem"].decode("ascii"),
            SSL_CLIENT_VERIFY_HEADER_NAME: "SUCCESS",
        },
    )

    mtls_fp = generate_fingerprint(ca_and_leaf["leaf_pem"])
    now = datetime.now(timezone.utc)
    claims = {
        "iss": f"ura:{ura_number}",
        "sub": f"ura:{ura_number}",
        "aud": "https://otherhost/token",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "jti": "unique-jti-aud",
        "cnf": {"x5t#S256": mtls_fp},
    }
    x5c = _x5c_list_from_certs(ca_and_leaf["leaf_cert"], ca_and_leaf["ca_cert"])
    assertion = jwt.encode(claims, key=ca_and_leaf["leaf_key"], algorithm="RS256", headers={"x5c": x5c})

    with pytest.raises(OAuthInvalidClientError) as e:
        svc.validate(
            grant_type="client_credentials",
            scope="read",
            client_assertion_type=CLIENT_ASSERTION_TYPE,
            client_assertion=assertion,
            request=req,
        )
    assert "aud mismatch" in str(e.value)


def test_generate_token_persists_entity(oauth_service):
    svc, repo, cfg = oauth_service

    token = svc.generate_token(ura_number=UraNumber("12345678"), scopes=["read"])
    assert token.startswith("nvi_tok_v1_")

    assert len(repo.added) == 1
    ent = repo.added[0]

    # entity fields
    assert ent.ura_number == "12345678"
    assert ent.scopes == "read"
    assert ent.token_sha256 == hashlib.sha256(token.encode("utf-8")).hexdigest()

    # expires should be in the future
    assert ent.expires_at > ent.created_at
    assert ent.expires_at <= ent.created_at + timedelta(seconds=cfg.token_lifetime_seconds + 1)


def test_verify_rejects_missing_header(oauth_service):
    svc, _repo, _cfg = oauth_service
    req = _make_request("https://testserver/anything", {})
    with pytest.raises(HTTPException) as e:
        svc.verify(req)
    assert e.value.status_code == 401


def test_verify_rejects_invalid_token(oauth_service):
    svc, _repo, _cfg = oauth_service
    req = _make_request("https://testserver/anything", {"authorization": "Bearer does-not-exist"})
    with pytest.raises(HTTPException) as e:
        svc.verify(req)
    assert e.value.status_code == 401
    assert e.value.detail == "Invalid token"


def test_verify_rejects_expired_token(oauth_service):
    svc, repo, _cfg = oauth_service

    token = svc.generate_token(ura_number=UraNumber("12345678"), scopes=["read"])
    ent = repo.added[0]
    ent.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    req = _make_request("https://testserver/anything", {"authorization": f"Bearer {token}"})
    with pytest.raises(HTTPException) as e:
        svc.verify(req)
    assert e.value.status_code == 401
    assert e.value.detail == "Token expired"


def test_verify_rejects_revoked_token(oauth_service):
    svc, repo, _cfg = oauth_service
    token = svc.generate_token(ura_number=UraNumber("12345678"), scopes=["read"])
    ent = repo.added[0]
    ent.revoked = True

    req = _make_request("https://testserver/anything", {"authorization": f"Bearer {token}"})
    with pytest.raises(HTTPException):
        svc.verify(req)
