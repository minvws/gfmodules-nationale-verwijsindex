from app.config import (
    Config,
    ConfigApp,
    ConfigClientOAuth,
    ConfigDatabase,
    ConfigDeziRegister,
    ConfigPseudonymApi,
    ConfigStats,
    ConfigTelemetry,
    LogLevel,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
            provider_id="84de3f9c-0113-4fbb-af4b-215715e631bd",
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
        dezi_register=ConfigDeziRegister(
            uzi_server_certificate_ca_cert_path="/test/secrets/ca.crt",
            dezi_register_trusted_signing_certs_store_path="/test/secrets/nvi/",
        ),
        client_oauth=ConfigClientOAuth(
            jwks_url="http://example.com/.well-known/jwks.json",
            issuer="http://example.com/",
            audience="test-audience",
            enabled=True,
            override_ura_number="12345678",
        ),
    )
