import pytest
from pydantic import SecretStr, ValidationError

from app.config import (
    Config,
    ConfigApp,
    ConfigAuthorizationHeaders,
    ConfigCryptoServiceApi,
    ConfigDatabase,
    ConfigLogging,
    ConfigPagination,
    ConfigTelemetry,
    ConfigUvicorn,
    LogLevel,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
        ),
        logging=ConfigLogging(
            syslog_path=None,
            application_id="nationale-verwijsindex",
            include_traces=True,
            console_streams=["debug"],
        ),
        database=ConfigDatabase(
            dsn=SecretStr("sqlite:///:memory:"),
            create_tables=True,
        ),
        crypto_service_api=ConfigCryptoServiceApi(
            endpoint="http://example.com",
            timeout=30,
            mtls_cert=None,
            mtls_key=None,
            verify_ca=True,
        ),
        telemetry=ConfigTelemetry(
            metrics_enabled=False,
            endpoint=None,
            service_name=None,
        ),
        uvicorn=ConfigUvicorn(
            docs_url="/docs",
            redoc_url="/redoc",
            swagger_enabled=True,
            ssl_base_dir="/ssl",
            ssl_cert_file="/file.cert",
            ssl_key_file="/file.key",
        ),
        authorization_headers=ConfigAuthorizationHeaders(
            expected_audiences=["test-audience"],
        ),
    )


def test_pagination_defaults_when_the_section_is_missing() -> None:
    config = get_test_config()

    assert config.pagination.default_page_size == 50
    assert config.pagination.max_page_size == 100


def test_pagination_rejects_a_default_larger_than_the_maximum() -> None:
    with pytest.raises(ValidationError):
        ConfigPagination(default_page_size=200, max_page_size=100)
