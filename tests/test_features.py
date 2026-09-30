from app.config import Config
from app.features import FEATURES, enabled_features
from tests.test_config import get_test_config


def _config(crypto_service_api_enabled: bool) -> Config:
    config = get_test_config()
    config.crypto_service_api.enabled = crypto_service_api_enabled
    return config


def _ids(config: Config) -> list[str]:
    return [feature.id for feature in enabled_features(config)]


def test_all_features_enabled_with_crypto_service_api() -> None:
    assert _ids(_config(crypto_service_api_enabled=True)) == [feature.info.id for feature in FEATURES]


def test_pseudonym_resolution_follows_crypto_service_api_flag() -> None:
    assert "pseudonym_resolution" in _ids(_config(crypto_service_api_enabled=True))
    assert "pseudonym_resolution" not in _ids(_config(crypto_service_api_enabled=False))


def test_core_features_are_always_enabled() -> None:
    ids = _ids(_config(crypto_service_api_enabled=False))

    assert ids == ["localization", "registrations", "fhir_localization_list"]


def test_feature_ids_are_unique() -> None:
    ids = [feature.info.id for feature in FEATURES]

    assert len(ids) == len(set(ids))
