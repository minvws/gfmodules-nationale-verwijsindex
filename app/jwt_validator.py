import base64
import logging
from typing import Any, Dict, List

import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, padding, rsa
from cryptography.x509 import Certificate

from app.models.dezi import DeziSigningCert

logger = logging.getLogger(__name__)


class JwtValidationError(Exception):
    """Exception raised when JWT validation fails."""

    pass


class JwtValidator:
    """Validator for JWT tokens using CA certificate validation."""

    def __init__(
        self,
        ca_certificate: Certificate,
        dezi_register_signing_certificates: List[DeziSigningCert],
    ) -> None:
        """
        Initialize JWT validator.

        Args:
            ca_certificate: The parsed CA certificate
            dezi_register_signing_certificates: List of certificates with JWK
        """
        self._ca_cert = ca_certificate
        self.dezi_register_signing_certificates = dezi_register_signing_certificates

    def __load_cert_chain_from_x5c(self, x5c_list: List[str]) -> List[Certificate]:
        """Decode x5c entries into X.509 certificate objects."""
        try:
            return [x509.load_der_x509_certificate(base64.b64decode(cert), default_backend()) for cert in x5c_list]
        except Exception as e:
            raise JwtValidationError(f"Failed to parse x5c certificate chain: {e}")

    def __validate_cert_chain(self, cert_chain: List[Certificate], trusted_ca: Certificate) -> None:
        """Validate that the signing certificate is issued by the trusted CA."""
        leaf_cert = cert_chain[0]

        try:
            # Check subject and issuer match
            if leaf_cert.issuer != trusted_ca.subject:
                raise JwtValidationError("Issuer mismatch between JWT cert and trusted CA")

            if leaf_cert.signature_hash_algorithm is None:
                raise JwtValidationError("Leaf certificate has no signature hash algorithm")

            # Verify signature
            trusted_ca.public_key().verify(  # type: ignore
                signature=leaf_cert.signature,
                data=leaf_cert.tbs_certificate_bytes,
                padding=padding.PKCS1v15(),
                algorithm=leaf_cert.signature_hash_algorithm,
            )

        except Exception as e:
            raise JwtValidationError(f"Certificate validation failed: {e}")

    def __validate_lrs_jwt_claims(self, decoded_token: Dict[str, Any]) -> None:
        """Validate required claims in the main JWT token."""
        required_claims = ["case_nr", "dezi_jwt"]
        for claim in required_claims:
            if claim not in decoded_token:
                raise JwtValidationError(f"JWT token is missing '{claim}' claim")

    def __decode_jwt(
        self,
        public_key: (rsa.RSAPublicKey | ec.EllipticCurvePublicKey | ed25519.Ed25519PublicKey | ed448.Ed448PublicKey),
        jwt_token: str,
        override_verify_options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Validate JWT signature with a given public key, return payload if valid. Raises JwtValidationError if invalid."""
        verify_options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_nbf": True,
            "verify_aud": True,
        }
        if override_verify_options:
            verify_options.update(override_verify_options)

        # Use the certificate’s public key to check the JWT signature.
        try:
            verified = jwt.decode(
                jwt_token,
                key=public_key,
                options=verify_options,
                algorithms=["RS256"],
            )
        except Exception as e:
            raise JwtValidationError(f"JWT signature verification failed or token is invalid: {e}")
        if not isinstance(verified, dict):
            raise JwtValidationError(f"Invalid JWT decode result type: {type(verified)}")
        return verified

    def _find_cert_and_decode_dezi_jwt(self, dezi_jwt_token: str) -> Dict[str, Any]:
        """
        Decode the DEZI JWT token.
        Retrieve x5t if present, find matching certificate and decode with its public key.
        FIXME/NOTE: We do/cannot NOT validate the audience and expiration claim here.
        """
        header = jwt.get_unverified_header(dezi_jwt_token)
        x5t = header.get("x5t")

        if x5t:
            cert = next(
                (c for c in self.dezi_register_signing_certificates if c.x5t == x5t),
                None,
            )
            if not cert:
                raise JwtValidationError(
                    f"Dezi signing certificate with x5t '{x5t}' not in configured `dezi_register_trusted_signing_certs_store_path`."
                )
            result = self.__decode_jwt(
                cert.public_key,
                dezi_jwt_token,
                override_verify_options={"verify_exp": False, "verify_aud": False},
            )
            if not result:
                raise JwtValidationError(f"Failed to validate DEZI JWT with certificate from x5t: {x5t}")
            return result

        # If no x5t set in JWT header, try to validate JWT with known certs
        for cert in self.dezi_register_signing_certificates:
            try:
                return self.__decode_jwt(
                    cert.public_key,
                    dezi_jwt_token,
                    override_verify_options={"verify_exp": False, "verify_aud": False},
                )
            except JwtValidationError:
                continue
        raise JwtValidationError(
            "Failed to validate DEZI JWT with any of the configured certificates in `dezi_register_trusted_signing_certs_store_path`."
        )

    def _validate_dezi_jwt_claims(self, decoded_dezi_jwt: Dict[str, Any]) -> None:
        """
        Validate required claims in the DEZI JWT token.
            Currently it is not possible to check the audience claim as the value is normally the OIDC client ID and that is unknown in the NVI.
            Note that there is a possibility that the LRS puts in a different DEZI JWT and we do not know if that DEZI JWT was intended for that LRS/system in front of the LRS.
            We do check that a relationship claim (URA) in the DEZI JWT matches the URA of the LRS (Middleware cert check)
        """
        required_keys = [
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
        ]

        for key in required_keys:
            if key not in decoded_dezi_jwt:
                raise JwtValidationError(f"DEZI JWT token is missing '{key}' claim")

        # Validate relations array
        if not isinstance(decoded_dezi_jwt["relations"], list) or len(decoded_dezi_jwt["relations"]) == 0:
            raise JwtValidationError("DEZI JWT token 'relations' must be a non-empty array")

    def _validate_relation_keys(self, relation: Dict[str, Any]) -> None:
        """Validate required keys in a relation object."""
        relation_keys = ["entity_name", "roles", "ura"]
        for key in relation_keys:
            if key not in relation:
                raise JwtValidationError(f"DEZI JWT token is missing '{key}' claim in 'relations'")

    def _find_matching_ura_relation(self, decoded_dezi_jwt: Dict[str, Any], client_ura_number: str) -> None:
        """Find and return if relation URA matches the client URA number."""
        for relation in decoded_dezi_jwt["relations"]:
            self._validate_relation_keys(relation)
            if relation["ura"] == client_ura_number:
                logger.info(f"Found matching URA number '{client_ura_number}' in DEZI JWT relations")
                return None

        available_uras = [rel["ura"] for rel in decoded_dezi_jwt["relations"]]
        raise JwtValidationError(
            f"Client URA number '{client_ura_number}' does not match any URA in DEZI JWT relations: {available_uras}"
        )

    def __retrieve_leaf_cert_from_x5c(self, token: str) -> Certificate:
        """Parse header and extract leaf cert from x5c"""
        unverified_header = jwt.get_unverified_header(token)
        x5c = unverified_header.get("x5c")
        if not x5c:
            raise JwtValidationError("JWT is missing 'x5c' certificate chain")

        cert_chain = self.__load_cert_chain_from_x5c(x5c)
        if not cert_chain or len(cert_chain) == 0:
            raise JwtValidationError("JWT is missing 'x5c' certificate chain")
        leaf_cert = cert_chain[0]

        # Validate leaf certificate is issued by trusted CA
        self.__validate_cert_chain(cert_chain, self._ca_cert)

        return leaf_cert

    def __get_pub_key_from_cert(
        self, cert: Certificate
    ) -> rsa.RSAPublicKey | ec.EllipticCurvePublicKey | ed25519.Ed25519PublicKey | ed448.Ed448PublicKey:
        """
        Extract the public key from a certificate. And check for correct type
        """
        public_key = cert.public_key()
        if not isinstance(
            public_key,
            (rsa.RSAPublicKey | ec.EllipticCurvePublicKey | ed25519.Ed25519PublicKey | ed448.Ed448PublicKey),
        ):
            raise JwtValidationError(f"Invalid public key type, type {type(public_key)} is not supported")
        return public_key

    def validate_lrs_jwt(self, token: str, client_ura_number: str) -> Any:
        """
        Validate a LRS JWT
        """
        try:
            # Get leaf cert from x5c from LRS jwt header
            leaf_cert = self.__retrieve_leaf_cert_from_x5c(token)
            # Get public key from leaf cert
            public_key = self.__get_pub_key_from_cert(leaf_cert)

            # Decode and validate main JWT claims
            decoded_token = self.__decode_jwt(public_key, token)
            self.__validate_lrs_jwt_claims(decoded_token)

            # Decode and validate DEZI JWT
            decoded_dezi_jwt = self._find_cert_and_decode_dezi_jwt(decoded_token["dezi_jwt"])
            self._validate_dezi_jwt_claims(decoded_dezi_jwt)

            # Validate URA number matches a relation
            self._find_matching_ura_relation(decoded_dezi_jwt, client_ura_number)

            logger.info("JWT validation successful")
            return decoded_token
        except Exception as e:
            raise JwtValidationError(f"JWT validation failed: {e}")
