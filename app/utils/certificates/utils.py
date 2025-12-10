import logging
import textwrap
from pathlib import Path
from typing import List

from cryptography import x509

logger = logging.getLogger(__name__)

_CERT_START = "-----BEGIN CERTIFICATE-----"
_CERT_END = "-----END CERTIFICATE-----"


def load_one_certificate_file(path: str) -> str:
    """
    Load a certificate file from the given path.

    Args:
        path (str): Path to the certificate file to read.
        example: "path/certificate.crt"

    Returns:
        the content of a ceritifacte as `str`
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found at: {file_path}")

    with open(file_path, "r") as file:
        try:
            cert_data = file.read()
        except IsADirectoryError as e:
            logger.warning("Error occurred while reading file")
            raise e

    return cert_data


def load_many_certificate_files(dir: str) -> List[str]:
    """
    Load a certificates file from the given directory.

    Args:
        dir (str): Path to the certificate directory to read.
        example: "path/certificate/"

    Returns:
        a `List` that holds certificates content.
    """
    file_path = Path(dir)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found at: {file_path}")

    return [load_one_certificate_file(str(f)) for f in file_path.iterdir()]


def create_certificate(cert: str) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(cert.encode())
    except Exception as e:
        raise RuntimeError(f"Unable to create CA certificate from path {cert} with error {e}")


def load_certificate(cert_path: str) -> x509.Certificate:
    """Load and parse CA certificate from file path."""
    cert_str = load_one_certificate_file(cert_path)
    return create_certificate(cert_str)


def enforce_cert_newlines(cert_data: str) -> str:
    cert_data = cert_data.split(_CERT_START)[-1].split(_CERT_END)[0].strip()
    result = _CERT_START
    result += "\n"
    result += "\n".join(textwrap.wrap(cert_data.replace(" ", ""), 64))
    result += "\n"
    result += _CERT_END

    return result
