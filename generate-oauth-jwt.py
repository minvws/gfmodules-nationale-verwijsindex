import argparse
import base64
import hashlib
import sys
import time
import uuid
from typing import List, Optional

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from uzireader.uziserver import UziServer

"""
Utility to generate a client_assertion JWT for OAuth2 client_credentials

Usage:

    poetry run python generate-oauth-jwt.py \
        --mtls-cert secrets/epd1.ldn.crt \
        --signing-cert secrets/nvi.crt \
        --signing-key secrets/nvi.key \
        --expires-in 86400 \
        --include-x5c \
        --scope nvi:read \
        --token-url <url>/oauth/token \
        --out test.jwt

    - Signing-cert and signing-key are the certificates that created the UZI server TLS cert (UZI server CA).

The generated JWT can then be used as the client_assertion parameter in the token request.
"""


def b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def load_cert_pem(path: str) -> x509.Certificate:
    with open(path, "rb") as f:
        data = f.read()
    return x509.load_pem_x509_certificate(data)


def load_private_key_pem(path: str, password: Optional[str]) -> object:
    with open(path, "rb") as f:
        key_bytes = f.read()
    pw = password.encode("utf-8") if password else None
    return serialization.load_pem_private_key(key_bytes, password=pw)


def cert_thumbprint_x5t_s256(cert: x509.Certificate) -> str:
    der = cert.public_bytes(serialization.Encoding.DER)
    digest = hashlib.sha256(der).digest()
    return b64url_nopad(digest)


def cert_to_x5c_b64(cert: x509.Certificate) -> str:
    der = cert.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate OAuth2 client_assertion JWT for /token (client_credentials).")
    ap.add_argument("--token-url", required=True, help="Audience: exact token endpoint URL (aud).")
    ap.add_argument("--mtls-cert", help="Path to mTLS PEM.")

    # Signing material
    ap.add_argument("--signing-cert", help="Path to PEM signing certificate.")
    ap.add_argument("--signing-key", help="Path to PEM signing private key (matches signing-cert).")

    ap.add_argument("--expires-in", type=int, default=300, help="JWT lifetime in seconds (default 300).")
    ap.add_argument("--include-x5c", action="store_true", help="Include x5c certificate chain in JWT header.")
    ap.add_argument("--scope", default=None, help="Optional scope claim.")
    ap.add_argument("--out", default="-", help="Output file (default: stdout).")

    args = ap.parse_args()

    # Load mTLS cert and compute thumbprint
    mtls_cert = load_cert_pem(args.mtls_cert)
    mtls_x5t_s256 = cert_thumbprint_x5t_s256(mtls_cert)

    # Load signing key + cert
    cert_chain: List[x509.Certificate] = []
    if not (args.signing_cert and args.signing_key):
        ap.error("Provide --signing-cert and --signing-key.")
    signing_cert = load_cert_pem(args.signing_cert)
    signing_key = load_private_key_pem(args.signing_key, password=None)

    # Get the URA from the signing cert's subject CN
    with open(args.signing_cert, "r", encoding="utf-8") as f:
        cert_pem = f.read()
    uzi_data = UziServer(verify="SUCCESS", cert=cert_pem)
    ura_number = uzi_data["SubscriberNumber"]

    alg = "RS256"

    now = int(time.time())
    jti = str(uuid.uuid4())

    # Client Assertion claims (common RFC7523 pattern)
    claims = {
        "iss": ura_number,
        "sub": ura_number,
        "aud": args.token_url,
        "iat": now,
        "exp": now + int(args.expires_in),
        "jti": jti,

        # Certificate binding (mTLS fingerprint)
        "cnf": {"x5t#S256": mtls_x5t_s256},
    }
    if args.scope:
        claims["scope"] = args.scope

    # JWT header
    header = {
        "typ": "JWT",
        "alg": alg,
        "kid": cert_thumbprint_x5t_s256(signing_cert),
    }
    if args.include_x5c:
        chain = [signing_cert] + cert_chain
        header["x5c"] = [cert_to_x5c_b64(c) for c in chain]

    token = jwt.encode(
        payload=claims,
        key=signing_key,
        algorithm=alg,
        headers=header,
    )

    # PyJWT may return bytes in some versions
    if isinstance(token, bytes):
        token = token.decode("ascii")

    if args.out == "-" or args.out.lower() == "stdout":
        print(token)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(token)
            f.write("\n")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
