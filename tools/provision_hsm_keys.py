"""Provision NVI RSA-4096, HMAC-256 and AES-256 keys after database migrations.

Required environment (app.conf is not read):
- HSMAPI_URL (HTTPS), HSMAPI_MODULE, HSMAPI_SLOT;
- HSM_CERT, HSM_KEY, HSM_CA (mTLS certificate/key and trusted CA paths);
- ALLOWED_JWE_KEY_IDS (space-separated RSA labels), HASHING_KEY_ID,
  SECRET_KEY_ID (AES label, max 50 characters);
- DSN (libpq connection string; SELECT/INSERT on public.keys_info).
The mTLS identity needs HSM lookup/create rights.

Only an empty keys_info permits new AES/HMAC material. Existing history requires
a valid active AES registration and its original AES/HMAC keys. Missing material
requires coherent DB/HSM restoration, never replacement. Reruns reuse keys,
including after a failed DB insert; do not rotate keys concurrently.
Exit 0 on success, 1 with a fixed diagnostic code on stderr, without sensitive details.
"""

import base64
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self, cast
from urllib.parse import quote, urlsplit

import psycopg
import requests
from OpenSSL import crypto


class ProvisioningError(Exception):
    """Configuration or HSM state cannot safely support provisioning."""


class ConfigurationError(ProvisioningError):
    """Required configuration is invalid."""


class HsmRequestError(ProvisioningError):
    """An HSM request failed or has an uncertain outcome."""


class HsmObjectError(ProvisioningError):
    """Returned HSM objects cannot safely be used."""


class PersistentStateError(ProvisioningError):
    """Database registration state cannot safely be used."""


class RestoreRequiredError(ProvisioningError):
    """Initialized persistent identity material is missing."""


@dataclass(frozen=True)
class Config:
    url: str
    module: str
    slot: str
    cert: str
    key: str
    ca: str
    rsa_labels: tuple[str, ...]
    hashing_label: str
    secret_label: str
    dsn: str = field(repr=False)

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Self:
        def required(name: str) -> str:
            value = environ.get(name)
            if not value or not value.strip():
                raise ConfigurationError(f"Required setting {name} is missing or empty")
            if name in ("HSMAPI_MODULE", "HSMAPI_SLOT") and value in (".", ".."):
                raise ConfigurationError(f"{name} must not be a dot path segment")
            return value

        url = required("HSMAPI_URL")
        try:
            parsed = urlsplit(url)
            valid_url = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and "?" not in url
                and "#" not in url
                and "\\" not in url
                and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url)
            )
            # Accessing port also rejects malformed or out-of-range ports.
            _ = parsed.port
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ConfigurationError("HSMAPI_URL must be HTTPS without credentials, query, or fragment")

        rsa_labels = tuple(required("ALLOWED_JWE_KEY_IDS").split())
        hashing_label = required("HASHING_KEY_ID")
        secret_label = required("SECRET_KEY_ID")
        labels = (*rsa_labels, hashing_label, secret_label)
        if len(set(labels)) != len(labels):
            raise ConfigurationError("HSM labels must be unique across all key kinds")
        if len(secret_label) > 50:
            raise ConfigurationError("SECRET_KEY_ID must not exceed 50 characters")

        return cls(
            url=url,
            module=required("HSMAPI_MODULE"),
            slot=required("HSMAPI_SLOT"),
            cert=required("HSM_CERT"),
            key=required("HSM_KEY"),
            ca=required("HSM_CA"),
            rsa_labels=rsa_labels,
            hashing_label=hashing_label,
            secret_label=secret_label,
            dsn=required("DSN"),
        )


def _rsa_pkcs1_der(modulus: int, exponent: int) -> bytes:
    """Encode only PKCS#1's two-positive-INTEGER RSAPublicKey for an exact comparison."""

    def element(tag: int, value: bytes) -> bytes:
        size = len(value)
        if size < 128:
            length = bytes([size])
        else:
            size_bytes = size.to_bytes((size.bit_length() + 7) // 8, "big")
            length = bytes([0x80 | len(size_bytes)]) + size_bytes
        return bytes([tag]) + length + value

    integers = b"".join(
        element(0x02, value.to_bytes((value.bit_length() + 8) // 8, "big", signed=True))
        for value in (modulus, exponent)
    )
    return element(0x30, integers)


class HsmClient:
    def __init__(self, config: Config):
        self.config = config
        self.endpoint = f"{config.url.rstrip('/')}/hsm/{quote(config.module, safe='')}/{quote(config.slot, safe='')}"

    def ensure_key(self, label: str, kind: str, bits: int, *, allow_create: bool = True) -> None:
        expected_bits = {"rsa": 4096, "secret": 256, "aes": 256}
        if not isinstance(label, str) or not label.strip():
            raise ConfigurationError("HSM key label must not be empty")
        if kind not in expected_bits or type(bits) is not int or bits != expected_bits[kind]:
            raise ConfigurationError("Unsupported HSM key kind or size")

        objects = self._post("", {"label": label}, "objects")
        if objects:
            self._validate_objects(objects, label, kind, bits)
            return
        if not allow_create:
            raise RestoreRequiredError("Required HSM key is absent; creation is forbidden")

        # Never retry generation here: a lost response may already have created material.
        objects = self._post(f"/generate/{kind}", {"label": label, "bits": bits}, "result")
        self._validate_objects(objects, label, kind, bits)

    def _post(self, route: str, payload: dict[str, str | int], field: str) -> list[dict[str, Any]]:
        try:
            response = requests.post(
                self.endpoint + route,
                json=payload,
                cert=(self.config.cert, self.config.key),
                verify=self.config.ca,
                timeout=(10, 30),
                allow_redirects=False,
            )
            if not 200 <= response.status_code < 300:
                raise HsmRequestError("HSM request returned a non-success status")
            body = response.json()
        except (requests.RequestException, OSError, ValueError):
            # Response bodies and transport errors can contain key data or credentials.
            raise HsmRequestError("HSM request failed or its outcome is uncertain; re-check before retrying") from None

        if not isinstance(body, dict) or any(name in body for name in ("error", "errors", "detail")):
            raise HsmRequestError("HSM response is malformed or reports an API error")
        objects = body.get(field)
        if not isinstance(objects, list) or any(not isinstance(obj, dict) for obj in objects):
            raise HsmObjectError("HSM response must contain an object list")
        return objects

    @staticmethod
    def _validate_objects(objects: list[dict[str, Any]], label: str, kind: str, bits: int) -> None:
        expected_classes = ("PUBLIC_KEY", "PRIVATE_KEY") if kind == "rsa" else ("SECRET_KEY",)
        expected_type = {"rsa": "RSA", "secret": "GENERIC_SECRET", "aes": "AES"}[kind]
        if len(objects) != len(expected_classes):
            raise HsmObjectError("HSM key has an incomplete or ambiguous object set")

        for obj in objects:
            if (
                obj.get("LABEL") != label
                or obj.get("CLASS") not in expected_classes
                or obj.get("KEY_TYPE") != expected_type
            ):
                raise HsmObjectError("HSM key label, class, or type is incompatible")
            size_field, expected_size = ("MODULUS_BITS", bits) if kind == "rsa" else ("VALUE_LEN", bits // 8)
            if size_field in obj and (type(obj[size_field]) is not int or obj[size_field] != expected_size):
                raise HsmObjectError("HSM key exposes an incompatible or malformed size")

        for expected_class in expected_classes:
            if sum(obj["CLASS"] == expected_class for obj in objects) != 1:
                raise HsmObjectError("HSM key has duplicate or missing object classes")
        if kind == "rsa":
            identities = [obj.get("ID") for obj in objects]
            if any(not isinstance(identity, str) for identity in identities) or identities[0] != identities[1]:
                raise HsmObjectError("HSM RSA public/private identities are missing or inconsistent")
            HsmClient._validate_rsa_material(objects, bits)

    @staticmethod
    def _validate_rsa_material(objects: list[dict[str, Any]], bits: int) -> None:
        def number(value: object) -> int:
            # PKCS#11 byte attributes are serialized as complete hex-encoded bytes.
            if not isinstance(value, str) or re.fullmatch(r"(?:[0-9a-fA-F]{2})+", value) is None:
                raise HsmObjectError("HSM RSA public component is malformed")
            return int(value, 16)

        moduli: set[int] = set()
        exponents: set[int] = set()
        for obj in objects:
            if "MODULUS" in obj:
                moduli.add(number(obj["MODULUS"]))
            if "PUBLIC_EXPONENT" in obj:
                exponents.add(number(obj["PUBLIC_EXPONENT"]))
            if "publickey" in obj:
                pem = obj["publickey"]
                if not isinstance(pem, str):
                    raise HsmObjectError("HSM public key is malformed")
                envelope = re.fullmatch(
                    r"-----BEGIN (PUBLIC KEY|RSA PUBLIC KEY)-----\r?\n"
                    r"([A-Za-z0-9+/=\r\n]+)-----END \1-----",
                    pem.strip(" \t\r\n"),
                )
                if envelope is None:
                    raise HsmObjectError("HSM public key is malformed")
                try:
                    encoded = envelope[2].replace("\r", "").replace("\n", "").encode("ascii")
                    payload = base64.b64decode(encoded, validate=True)
                    if base64.b64encode(payload) != encoded:
                        raise HsmObjectError("HSM public key has malformed base64")
                    public_key = crypto.load_publickey(crypto.FILETYPE_PEM, pem.encode("ascii"))
                    if public_key.type() != crypto.TYPE_RSA or public_key.bits() != bits:
                        raise HsmObjectError("HSM public key must be RSA-4096")
                    # The OpenSSL RSA check narrows this broadly typed conversion.
                    numbers = cast(Any, public_key.to_cryptography_key()).public_numbers()
                    # OpenSSL may ignore extra DER even inside a single PEM body or
                    # SPKI BIT STRING. Compare every decoded byte with the parsed key.
                    expected = (
                        crypto.dump_publickey(crypto.FILETYPE_ASN1, public_key)
                        if envelope[1] == "PUBLIC KEY"
                        else _rsa_pkcs1_der(numbers.n, numbers.e)
                    )
                    if payload != expected:
                        raise HsmObjectError("HSM public key contains malformed or extra encoded data")
                except (crypto.Error, ValueError):
                    raise HsmObjectError("HSM public key is malformed") from None
                moduli.add(numbers.n)
                exponents.add(numbers.e)

        if any(modulus.bit_length() != bits for modulus in moduli):
            raise HsmObjectError("HSM RSA modulus must be RSA-4096")
        if any(exponent < 3 or exponent % 2 == 0 for exponent in exponents):
            raise HsmObjectError("HSM RSA public exponent is invalid")
        if len(moduli) > 1 or len(exponents) > 1:
            raise HsmObjectError("HSM RSA public components are inconsistent")
        if moduli and exponents and next(iter(exponents)) >= next(iter(moduli)):
            raise HsmObjectError("HSM RSA public exponent is invalid")


def provision(config: Config) -> None:
    """Bootstrap only an empty database; preserve initialized referral identity."""
    with psycopg.connect(config.dsn, connect_timeout=10) as connection, connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("nvi-hsm-key-provisioning",))
        rows = connection.execute(
            "SELECT id, label, mechanism, active, deleted_at FROM public.keys_info",
            (),
        ).fetchall()
        if rows:
            registrations = [
                row for row in rows if row[1] == config.secret_label or (row[3] is True and row[4] is None)
            ]
            if len(registrations) != 1:
                raise PersistentStateError("Initialized AES registration state requires restoration or is ambiguous")
            _, label, mechanism, active, deleted_at = registrations[0]
            if label != config.secret_label or mechanism != "AES_CBC" or active is not True or deleted_at is not None:
                raise PersistentStateError("Existing AES registration is incompatible")

        client = HsmClient(config)
        # Both AES and HMAC determine durable referral identity. Validate protected
        # material before any generation; even inactive/deleted DB history is not fresh.
        client.ensure_key(config.secret_label, "aes", 256, allow_create=not rows)
        client.ensure_key(config.hashing_label, "secret", 256, allow_create=not rows)
        for label in config.rsa_labels:
            client.ensure_key(label, "rsa", 4096)

        if not rows:
            connection.execute(
                "INSERT INTO public.keys_info (label, mechanism, active) VALUES (%s, %s, %s)",
                (config.secret_label, "AES_CBC", True),
            )


def main(environ: Mapping[str, str] | None = None) -> int:
    try:
        provision(Config.from_env(os.environ if environ is None else environ))
    except Exception as error:  # noqa: BLE001 - redact even unexpected exception details at the CLI boundary.
        # Classify by trusted exception types, never their messages or attributes.
        codes: dict[type[Exception], str] = {
            ConfigurationError: "CONFIG_INVALID",
            HsmRequestError: "HSM_REQUEST_FAILED",
            HsmObjectError: "HSM_OBJECT_INVALID",
            PersistentStateError: "STATE_INVALID",
            RestoreRequiredError: "RESTORE_REQUIRED",
        }
        code = codes.get(type(error), "UNEXPECTED_ERROR")
        if isinstance(error, psycopg.Error):
            code = "DATABASE_FAILED"
        print(
            f"HSM key provisioning failed [{code}].",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
