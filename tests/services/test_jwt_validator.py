import base64
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List
from unittest.mock import patch

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from cryptography.x509 import Certificate

from app.data import UraNumber
from app.services.jwt_validator import DeziSigningCert, JwtValidationError, JwtValidator


def _generate_rsa_private_key() -> rsa.RSAPrivateKey:
    """Generate a standard RSA private key for testing."""
    # Smaller keysize for testing as it is faster. FOR PRODUCTION KEYS, USE A LARGER KEY SIZE.
    return rsa.generate_private_key(public_exponent=65537, key_size=1024)  # NOSONAR


def _create_test_certificate(
    private_key: rsa.RSAPrivateKey,
    subject_name: str,
    issuer_name: str,
    signing_key: rsa.RSAPrivateKey | None = None,
    is_ca: bool = False,
) -> x509.Certificate:
    """Create a test certificate with the given parameters."""
    if signing_key is None:
        signing_key = private_key

    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, subject_name)])
    issuer = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, issuer_name)])

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
    )
    now = datetime.now()
    builder = builder.not_valid_before(now).not_valid_after(now + timedelta(days=365))

    if is_ca:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)

    return builder.sign(signing_key, hashes.SHA256())


def _get_cert_public_key(
    cert: x509.Certificate,
) -> rsa.RSAPublicKey | ec.EllipticCurvePublicKey | ed25519.Ed25519PublicKey | ed448.Ed448PublicKey:
    """Extract the public key from a certificate."""
    public_key = cert.public_key()
    if not isinstance(
        public_key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey, ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)
    ):
        raise TypeError(f"Unsupported public key type in certificate: {type(public_key)}")
    return public_key


@pytest.fixture
def rsa_private_key():
    """Generate RSA private key for testing."""
    return _generate_rsa_private_key()


@pytest.fixture
def ca_private_key():
    """Generate CA private key for testing."""
    return _generate_rsa_private_key()


@pytest.fixture
def ca_certificate(ca_private_key):
    """Create CA certificate for testing."""
    return _create_test_certificate(
        private_key=ca_private_key, subject_name="Test CA", issuer_name="Test CA", is_ca=True
    )


@pytest.fixture
def leaf_certificate(rsa_private_key, ca_private_key):
    """Create leaf certificate for testing."""
    return _create_test_certificate(
        private_key=rsa_private_key,
        subject_name="Test Leaf",
        issuer_name="Test CA",
        signing_key=ca_private_key,
        is_ca=False,
    )


def helper_create_jwt_validator(ca_certificate: Certificate, simple_dezi_signing_cert: DeziSigningCert) -> JwtValidator:
    """Create JWT validator for testing."""
    with (
        patch("app.services.jwt_validator.JwtValidator._load_certificate") as mock_load_cert,
        patch("app.services.jwt_validator.JwtValidator._load_dezi_signing_certificates") as mock_load_dezi_certs,
    ):
        mock_load_cert.return_value = ca_certificate
        mock_load_dezi_certs.return_value = [simple_dezi_signing_cert]
        return JwtValidator(
            uzi_server_certificate_ca_cert_path="dummy_path",
            dezi_register_trusted_signing_certs_store_path="dummy_dezi_path",
        )


@pytest.fixture
def jwt_validator(ca_certificate, simple_dezi_signing_cert):
    """Fixture to create JWT validator for testing."""
    dezi_cert, _ = simple_dezi_signing_cert
    return helper_create_jwt_validator(ca_certificate, dezi_cert)


@pytest.fixture
def jwt_with_x5c():
    """Fixture to create JWT with x5c header."""

    def _create_jwt_with_x5c(
        payload: Dict[str, Any], signing_key: rsa.RSAPrivateKey, x5c_certs: List[Certificate]
    ) -> str:
        x5c = [base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode("utf-8") for cert in x5c_certs]
        headers = {"x5c": x5c}
        return jwt.encode(payload, signing_key, algorithm="RS256", headers=headers)

    return _create_jwt_with_x5c


@pytest.fixture
def dezi_jwt_helper():
    """Fixture to create DEZI JWT with x5t headers."""

    def _create_dezi_jwt(payload: Dict[str, Any], signing_key: rsa.RSAPrivateKey, x5t: str) -> str:
        headers = {"x5t": x5t}
        return jwt.encode(payload, signing_key, algorithm="RS256", headers=headers)

    return _create_dezi_jwt


@pytest.fixture
def standard_jwt_payload() -> Callable[..., Dict[str, Any]]:
    """Fixture for standard JWT payload structure."""

    def _create_payload(dezi_jwt_token: str = "dummy_dezi_jwt", **overrides: Any) -> Dict[str, Any]:
        base_payload = {
            "sub": "test-subject",
            "iat": 1234567890,
            "exp": 9999999999,
            "case_nr": "1234",
            "dezi_jwt": dezi_jwt_token,
            "breaking_glass": False,
        }
        base_payload.update(overrides)
        return base_payload

    return _create_payload


@pytest.fixture
def dezi_payload_factory() -> Callable[..., Dict[str, Any]]:
    """Fixture for creating DEZI JWT payload structures."""

    def _create_dezi_payload(**overrides: Any) -> Dict[str, Any]:
        base_payload = {
            "aud": "",
            "exp": 9999999999,
            "initials": "T.E.S.T.",
            "iss": "https://example.com",
            "loa_authn": "https://example.com",
            "loa_uzi": "https://example.com",
            "nbf": 1234567899,
            "relations": [{"entity_name": "TestEntity", "roles": ["01.010"], "ura": "12341234"}],
            "sub": "test_sub",
            "surname": "Test",
            "surname_prefix": "test",
            "uzi_id": "999991772",
        }
        base_payload.update(overrides)
        return base_payload

    return _create_dezi_payload


@pytest.fixture
def base_relation_factory() -> Callable[..., Dict[str, Any]]:
    """Fixture for creating relation objects used in DEZI payloads."""

    def _create_relation(**overrides: Any) -> Dict[str, Any]:
        base_relation = {"entity_name": "TestEntity", "roles": ["01.010"], "ura": "12341234"}
        base_relation.update(overrides)
        return base_relation

    return _create_relation


@pytest.fixture
def simple_dezi_signing_cert() -> tuple[DeziSigningCert, rsa.RSAPrivateKey]:
    """Create DEZI certificate with x5t."""
    dezi_private_key = _generate_rsa_private_key()
    dezi_cert = _create_test_certificate(
        private_key=dezi_private_key,
        subject_name="DEZI Signer",
        issuer_name="DEZI CA",
        is_ca=False,
    )
    return DeziSigningCert(
        certificate=dezi_cert, x5t="test-x5t", public_key=_get_cert_public_key(dezi_cert)
    ), dezi_private_key


def test_cert_chain_does_not_exist(rsa_private_key, ca_certificate, simple_dezi_signing_cert):
    """Test scenario: x5c certificate chain does not exist in JWT header."""
    payload = {"sub": "test", "iat": 1234567890, "exp": 9999999999}
    jwt_validator = helper_create_jwt_validator(ca_certificate, simple_dezi_signing_cert)

    # Create JWT without x5c header
    token = jwt.encode(payload, rsa_private_key, algorithm="RS256")

    with pytest.raises(JwtValidationError, match="JWT is missing 'x5c' certificate chain"):
        jwt_validator.validate_lrs_jwt(token, UraNumber("12341234"))


def test_cert_chain_failed_to_parse(rsa_private_key, jwt_validator):
    """Test scenario: Certificate chain failed to parse."""
    payload = {"sub": "test", "iat": 1234567890, "exp": 9999999999}

    # Create JWT with invalid x5c content
    headers = {"x5c": ["INVALID_BASE64_CONTENT"]}

    token = jwt.encode(payload, rsa_private_key, algorithm="RS256", headers=headers)

    with pytest.raises(JwtValidationError, match="Failed to parse x5c certificate chain"):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_cert_chain_fails_to_validate(jwt_validator):
    """Test scenario: Certificate chain fails to validate against CA."""
    # Create a different CA that didn't issue the leaf certificate
    different_ca_key = _generate_rsa_private_key()

    # Create leaf cert signed by different CA
    different_leaf_key = _generate_rsa_private_key()
    different_leaf_cert = _create_test_certificate(
        private_key=different_leaf_key,
        subject_name="Different Leaf",
        issuer_name="Different CA",
        signing_key=different_ca_key,
        is_ca=False,
    )

    payload = {"sub": "test", "iat": 1234567890, "exp": 9999999999}

    # Create JWT with certificate from different CA
    token = jwt.encode(
        payload,
        different_leaf_key,
        algorithm="RS256",
        headers={
            "x5c": [base64.b64encode(different_leaf_cert.public_bytes(serialization.Encoding.DER)).decode("utf-8")]
        },
    )

    with pytest.raises(JwtValidationError, match="Certificate validation failed"):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_expired_jwt_token(rsa_private_key, leaf_certificate, jwt_with_x5c, jwt_validator):
    """Test scenario: JWT token has expired."""
    payload = {"sub": "test", "iat": 1234567890, "exp": 1234567891}
    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    with pytest.raises(
        JwtValidationError, match="JWT signature verification failed or token is invalid: Signature has expired"
    ):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_invalid_signature(leaf_certificate, jwt_validator):
    """Test scenario: JWT signature is invalid."""
    payload = {"sub": "test", "iat": 1234567890, "exp": 9999999999}
    different_key = _generate_rsa_private_key()

    token = jwt.encode(
        payload,
        different_key,
        algorithm="RS256",
        headers={"x5c": [base64.b64encode(leaf_certificate.public_bytes(serialization.Encoding.DER)).decode("utf-8")]},
    )

    with pytest.raises(JwtValidationError, match="Signature verification failed"):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_issuer_mismatch_validation(jwt_validator):
    """Test scenario: Issuer mismatch between JWT cert and trusted CA."""
    # Create a self-signed certificate (issuer != CA subject)
    self_signed_key = _generate_rsa_private_key()
    self_signed_cert = _create_test_certificate(
        private_key=self_signed_key,
        subject_name="Self Signed",
        issuer_name="Self Signed",
        is_ca=False,
    )

    payload = {"sub": "test", "iat": 1234567890, "exp": 9999999999}
    token = jwt.encode(
        payload,
        self_signed_key,
        algorithm="RS256",
        headers={"x5c": [base64.b64encode(self_signed_cert.public_bytes(serialization.Encoding.DER)).decode("utf-8")]},
    )

    with pytest.raises(JwtValidationError, match="Issuer mismatch between JWT cert and trusted CA"):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_happy_flow_with_dezi_signature_validation(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    dezi_jwt_helper,
    standard_jwt_payload,
    dezi_payload_factory,
    simple_dezi_signing_cert,
):
    """Test scenario: Happy flow with DEZI JWT signature"""
    # Generate DEZI private key and certificate
    dezi_cert, dezi_private_key = simple_dezi_signing_cert

    # Create validator with DEZI signature certificates
    validator = helper_create_jwt_validator(ca_certificate, dezi_cert)

    dezi_payload = dezi_payload_factory()

    # Encode DEZI JWT with x5t header
    dezi_jwt_token = dezi_jwt_helper(dezi_payload, dezi_private_key, "test-x5t")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token, custom_claim="test_value")

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    # Should not raise any exception
    verified_payload = validator.validate_lrs_jwt(token, UraNumber("12341234"))

    assert verified_payload["sub"] == "test-subject"
    assert verified_payload["custom_claim"] == "test_value"
    assert verified_payload["iat"] == 1234567890
    assert verified_payload["exp"] == 9999999999


def test_unhappy_flow_wrong_dezi_public_key(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    dezi_jwt_helper,
    standard_jwt_payload,
    dezi_payload_factory,
):
    """Test scenario: Unhappy flow with wrong DEZI public key for signature validation."""
    # Generate a key pair for DEZI JWT signing
    dezi_private_key = _generate_rsa_private_key()

    # Generate a different key pair for the validator (wrong key)
    wrong_dezi_private_key = _generate_rsa_private_key()

    # Create certificate with wrong key
    wrong_dezi_cert = _create_test_certificate(
        private_key=wrong_dezi_private_key,
        subject_name="Wrong DEZI Signer",
        issuer_name="Wrong DEZI CA",
        is_ca=False,
    )

    # Create DeziSigningCert for wrong DEZI signing key
    wrong_dezi_cert_with_x5t = DeziSigningCert(
        certificate=wrong_dezi_cert, x5t="test-x5t", public_key=_get_cert_public_key(wrong_dezi_cert)
    )

    # Create validator with wrong certificate
    validator = helper_create_jwt_validator(ca_certificate, wrong_dezi_cert_with_x5t)

    dezi_payload = dezi_payload_factory()

    # Encode DEZI JWT with x5t header
    dezi_jwt_token = dezi_jwt_helper(dezi_payload, dezi_private_key, "test-x5t")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token, custom_claim="test_value")

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    # Should raise JwtValidationError due to signature mismatch
    with pytest.raises(JwtValidationError, match="Signature verification failed"):
        validator.validate_lrs_jwt(token, UraNumber("12341234"))


@pytest.mark.parametrize(
    "missing_claim,expected_error",
    [
        ("case_nr", "JWT token is missing 'case_nr' claim"),
        ("dezi_jwt", "JWT token is missing 'dezi_jwt' claim"),
        ("breaking_glass", "JWT token is missing 'breaking_glass' claim"),
    ],
)
def test_missing_main_jwt_claims(
    rsa_private_key, leaf_certificate, jwt_with_x5c, jwt_validator, standard_jwt_payload, missing_claim, expected_error
):
    """Test scenarios where main JWT is missing required claims."""
    # Create base payload and remove the specific claim
    payload = standard_jwt_payload()
    del payload[missing_claim]

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])
    with pytest.raises(JwtValidationError, match=expected_error):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_dezi_jwt_unknown_x5t(rsa_private_key, leaf_certificate, jwt_with_x5c, jwt_validator, standard_jwt_payload):
    """Test scenario: DEZI JWT has unknown x5t"""
    # Create DEZI JWT with unknown x5t
    dezi_private_key = _generate_rsa_private_key()

    # Unknown x5t
    dezi_jwt_token = jwt.encode(
        {"sub": "test", "iat": 1234567890, "exp": 9999999999},
        dezi_private_key,
        algorithm="RS256",
        headers={"x5t": "unknown-x5t"},
    )

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])
    with pytest.raises(
        JwtValidationError,
        match="Dezi signing certificate with x5t 'unknown-x5t' not in configured `dezi_register_trusted_signing_certs_store_path`.",
    ):
        jwt_validator.validate_lrs_jwt(token, "12341234")


def test_dezi_jwt_missing_x5t_fallback_success(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    standard_jwt_payload,
    dezi_payload_factory,
    simple_dezi_signing_cert,
):
    """Test scenario: DEZI JWT has no x5t header, falls back to trying all certificates and succeeds."""
    # Generate DEZI certificate
    dezi_cert_with_x5t, dezi_private_key = simple_dezi_signing_cert
    dezi_cert_with_x5t.x5t = "test-x5t"

    validator = helper_create_jwt_validator(ca_certificate, dezi_cert_with_x5t)

    dezi_payload = dezi_payload_factory()

    # Create DEZI JWT WITHOUT x5t header
    dezi_jwt_token = jwt.encode(dezi_payload, dezi_private_key, algorithm="RS256")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)
    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    verified_payload = validator.validate_lrs_jwt(token, UraNumber("12341234"))
    assert verified_payload["sub"] == "test-subject"


def test_dezi_jwt_missing_x5t_fallback_failure(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    standard_jwt_payload,
    dezi_payload_factory,
    simple_dezi_signing_cert,
):
    """Test scenario: DEZI JWT has no x5t header, tries all certificates but all fail."""
    # Generate DEZI private key but use a different certificate in validator
    dezi_private_key = _generate_rsa_private_key()

    # Create a different certificate for the validator (wrong key)
    wrong_dezi_cert_with_x5t, _ = simple_dezi_signing_cert
    wrong_dezi_cert_with_x5t.x5t = "test-x5t"

    validator = helper_create_jwt_validator(ca_certificate, wrong_dezi_cert_with_x5t)

    dezi_payload = dezi_payload_factory()

    # Create DEZI JWT WITHOUT x5t header using the correct key
    dezi_jwt_token = jwt.encode(dezi_payload, dezi_private_key, algorithm="RS256")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)
    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    with pytest.raises(
        JwtValidationError,
        match="Failed to validate DEZI JWT with any of the configured certificates in `dezi_register_trusted_signing_certs_store_path`.",
    ):
        validator.validate_lrs_jwt(token, UraNumber("12341234"))


@pytest.mark.parametrize(
    "missing_claim",
    [
        "aud",
        "exp",
        "initials",
        "iss",
        "loa_authn",
        "loa_uzi",
        "nbf",
        "relations",
        "sub",
        "surname",
        "surname_prefix",
        "uzi_id",
    ],
)
def test_dezi_jwt_missing_required_claims(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    dezi_jwt_helper,
    standard_jwt_payload,
    dezi_payload_factory,
    missing_claim,
    simple_dezi_signing_cert,
):
    """Test scenarios where DEZI JWT is missing required claims."""
    dezi_cert_with_x5t, dezi_private_key = simple_dezi_signing_cert
    dezi_cert_with_x5t.x5t = "test-x5t"

    validator = helper_create_jwt_validator(ca_certificate, dezi_cert_with_x5t)

    # Create base payload and remove the specific claim
    dezi_payload = dezi_payload_factory()
    del dezi_payload[missing_claim]

    dezi_jwt_token = dezi_jwt_helper(dezi_payload, dezi_private_key, "test-x5t")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])
    with pytest.raises(JwtValidationError, match=f"DEZI JWT token is missing '{missing_claim}' claim"):
        validator.validate_lrs_jwt(token, UraNumber("12341234"))


@pytest.mark.parametrize("missing_key", ["entity_name", "roles", "ura"])
def test_dezi_jwt_missing_relation_keys(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    dezi_jwt_helper,
    standard_jwt_payload,
    dezi_payload_factory,
    base_relation_factory,
    missing_key,
    simple_dezi_signing_cert,
):
    """Test scenarios where DEZI JWT relation objects are missing required keys."""
    # Generate DEZI certificate
    dezi_cert_with_x5t, dezi_private_key = simple_dezi_signing_cert
    dezi_cert_with_x5t.x5t = "test-x5t"

    validator = helper_create_jwt_validator(ca_certificate, dezi_cert_with_x5t)

    # Create relation and remove the specific key
    relation = base_relation_factory()
    del relation[missing_key]

    dezi_payload = dezi_payload_factory(relations=[relation])

    dezi_jwt_token = dezi_jwt_helper(dezi_payload, dezi_private_key, "test-x5t")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])
    with pytest.raises(JwtValidationError, match=f"DEZI JWT token is missing '{missing_key}' claim in 'relations'"):
        validator.validate_lrs_jwt(token, UraNumber("12341234"))


def test_ura_number_mismatch(
    rsa_private_key,
    leaf_certificate,
    ca_certificate,
    jwt_with_x5c,
    dezi_jwt_helper,
    standard_jwt_payload,
    dezi_payload_factory,
    base_relation_factory,
    simple_dezi_signing_cert,
):
    """Test scenario: Client URA number doesn't match any URA in DEZI JWT relations."""
    # Generate DEZI certificate
    dezi_cert_with_x5t, dezi_private_key = simple_dezi_signing_cert
    dezi_cert_with_x5t.x5t = "test-x5t"

    validator = helper_create_jwt_validator(ca_certificate, dezi_cert_with_x5t)

    # Create multiple relations with different URAs
    relations = [
        base_relation_factory(ura="11111111"),
        base_relation_factory(entity_name="Another Entity", roles=["01.020"], ura="22222222"),
    ]

    dezi_payload = dezi_payload_factory(relations=relations)

    dezi_jwt_token = dezi_jwt_helper(dezi_payload, dezi_private_key, "test-x5t")

    payload = standard_jwt_payload(dezi_jwt_token=dezi_jwt_token)

    token = jwt_with_x5c(payload, rsa_private_key, [leaf_certificate])

    # Request URA that's not in the relations
    with pytest.raises(
        JwtValidationError,
        match="Client URA number '99999999' does not match any URA in DEZI JWT relations: \\['11111111', '22222222'\\]",
    ):
        validator.validate_lrs_jwt(token, UraNumber("99999999"))
