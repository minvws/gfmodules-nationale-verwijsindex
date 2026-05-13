from app.config import (
    Config,
    ConfigApp,
    ConfigCryptoServiceApi,
    ConfigDatabase,
    ConfigOAuth,
    ConfigStats,
    ConfigTelemetry,
    ConfigUvicorn,
    LogLevel,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
        ),
        database=ConfigDatabase(
            dsn="sqlite:///:memory:",
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
            enabled=False,
            endpoint=None,
            service_name=None,
            tracer_name=None,
        ),
        stats=ConfigStats(enabled=False, host=None, port=None, module_name=None),
        uvicorn=ConfigUvicorn(
            docs_url="/docs",
            redoc_url="/redoc",
            swagger_enabled=True,
            ssl_base_dir="/ssl",
            ssl_cert_file="/file.cert",
            ssl_key_file="/file.key",
        ),
        oauth=ConfigOAuth(
            issuer="http://example.com/",
            audience="test-audience",
            override_ura_number="12345678",
        ),
    )
