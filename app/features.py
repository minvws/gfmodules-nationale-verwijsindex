from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.config import Config


class FeatureInfo(BaseModel):
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Feature:
    info: FeatureInfo
    enabled: Callable[[Config], bool]


FEATURES: list[Feature] = [
    Feature(
        info=FeatureInfo(
            id="localization",
            title="Localization",
            description="Localize the care providers that hold data about a patient, using an OPRF pseudonym",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="registrations",
            title="Registrations",
            description="Register and remove referrals between a pseudonymized patient and a care provider",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="fhir_localization_list",
            title="FHIR localization list",
            description="Manage referrals as FHIR List resources",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="pseudonym_resolution",
            title="Pseudonym resolution",
            description="Resolve pseudonyms via the NVI crypto service instead of a mock",
        ),
        enabled=lambda config: config.crypto_service_api.enabled,
    ),
]


def enabled_features(config: Config) -> list[FeatureInfo]:
    return [feature.info for feature in FEATURES if feature.enabled(config)]
