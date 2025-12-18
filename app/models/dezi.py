from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from cryptography.x509 import Certificate
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.utils.certificates.utils import get_x5t_from_certificate


class DeziSigningCert(BaseModel):
    certificate: Certificate
    x5t: str
    public_key: rsa.RSAPublicKey | ec.EllipticCurvePublicKey | ed25519.Ed25519PublicKey | ed448.Ed448PublicKey

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_x509_certificate(cls, certificate: Certificate) -> "DeziSigningCert":
        x5t = get_x5t_from_certificate(certificate)
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

        return cls(certificate=certificate, public_key=public_key, x5t=x5t)
