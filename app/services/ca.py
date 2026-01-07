import logging
from typing import Optional

from fastapi import Request
from OpenSSL import crypto

from app.config import ConfigOAuth

SSL_CLIENT_CERT_HEADER_NAME = "x-proxy-ssl_client_cert"
SSL_CLIENT_VERIFY_HEADER_NAME = "x-proxy-ssl_client_verify"

logger = logging.getLogger(__name__)


class CaService:
    def __init__(self, config: ConfigOAuth) -> None:
        self.config = config

        self._uzi_store = crypto.X509Store()
        self._uzi_store.load_locations(cafile=self.config.uzi_ca_cert)

        self._ldn_store = crypto.X509Store()
        self._ldn_store.load_locations(cafile=self.config.ldn_ca_cert)

    def is_uzi_server_certificate(self, request: Request) -> bool:
        """
        Determines if the server certificate is an UZI certificate signed by the UZI CA.
        """
        cert_pem = self.get_pem_from_request(request)
        if cert_pem is None:
            return False

        cert_x509 = crypto.load_certificate(crypto.FILETYPE_PEM, (cert_pem or "").encode("ascii"))
        ctx = crypto.X509StoreContext(self._uzi_store, cert_x509)
        try:
            ctx.verify_certificate()
            return True
        except crypto.X509StoreContextError:
            return False

    def is_ldn_server_certificate(self, request: Request) -> bool:
        """
        Determines if the server certificate is an LDN certificate signed by the LDN CA.
        """
        cert_pem = self.get_pem_from_request(request)
        if cert_pem is None:
            return False

        cert_x509 = crypto.load_certificate(crypto.FILETYPE_PEM, (cert_pem or "").encode("ascii"))
        ctx = crypto.X509StoreContext(self._ldn_store, cert_x509)
        try:
            ctx.verify_certificate()
            return True
        except crypto.X509StoreContextError:
            return False

    @staticmethod
    def get_pem_from_request(request: Request) -> Optional[str]:
        """
        Extracts and returns the PEM-encoded client certificate from the request headers.
        """
        cert_pem = request.headers.get(SSL_CLIENT_CERT_HEADER_NAME)
        verify_status = request.headers.get(SSL_CLIENT_VERIFY_HEADER_NAME)

        if not cert_pem or verify_status != "SUCCESS":
            logger.debug("Client certificate not found or verification failed.")
            return None

        cert_pem = cert_pem.replace("-----BEGIN CERTIFICATE-----", "-----BEGIN CERTIFICATE-----\n")
        cert_pem = cert_pem.replace("-----END CERTIFICATE-----", "\n-----END CERTIFICATE-----\n")
        return cert_pem
