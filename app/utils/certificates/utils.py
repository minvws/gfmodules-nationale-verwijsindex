import textwrap
from pathlib import Path

from cryptography import x509

_CERT_START = "-----BEGIN CERTIFICATE-----"
_CERT_END = "-----END CERTIFICATE-----"


def load_certificate(cert_path: str) -> x509.Certificate:
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


def enforce_cert_newlines(cert_data: str) -> str:
    cert_data = cert_data.split(_CERT_START)[-1].split(_CERT_END)[0].strip()
    result = _CERT_START
    result += "\n"
    result += "\n".join(textwrap.wrap(cert_data.replace(" ", ""), 64))
    result += "\n"
    result += _CERT_END

    return result
