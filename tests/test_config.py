from app.config import (
    Config,
    ConfigApp,
    ConfigClientOAuth,
    ConfigDatabase,
    ConfigOAuth,
    ConfigPseudonymApi,
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
        pseudonym_api=ConfigPseudonymApi(
            endpoint="http://example.com",
            timeout=30,
            mtls_cert="",
            mtls_key="",
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
            jwks_url="http://example.com/.well-known/jwks.json",
            audience="test-audience",
            enabled=False,
            override_ura_number="12345678",
        ),
        client_oauth=ConfigClientOAuth(
            issuer="http://example.com/",
            enabled=False,
        ),
    )
