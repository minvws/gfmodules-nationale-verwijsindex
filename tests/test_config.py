from app.config import (
    Config,
    ConfigApp,
    ConfigDatabase,
    ConfigDeziRegister,
    ConfigPseudonymApi,
    ConfigStats,
    ConfigTelemetry,
    ConfigUraMiddleware,
    LogLevel,
)


def get_test_config() -> Config:
    return Config(
        app=ConfigApp(
            loglevel=LogLevel.error,
            provider_id="84de3f9c-0113-4fbb-af4b-215715e631bd",
            authorization_service=False,
        ),
        database=ConfigDatabase(
            dsn="sqlite:///:memory:",
            create_tables=True,
        ),
        pseudonym_api=ConfigPseudonymApi(
            base_url="http://example.com",
            mtls_cert="",
            mtls_key="",
            mtls_ca="",
        ),
        telemetry=ConfigTelemetry(
            enabled=False,
            endpoint=None,
            service_name=None,
            tracer_name=None,
        ),
        stats=ConfigStats(enabled=False, host=None, port=None, module_name=None),
        ura_middleware=ConfigUraMiddleware(
            override_authentication_ura=None, use_authentication_ura_allowlist=False, allowlist_cache_in_seconds=40
        ),
        dezi_register=ConfigDeziRegister(
            uzi_server_certificate_ca_cert_path="/test/secrets/ca.crt",
            dezi_register_trusted_signing_certs_store_path="/test/secrets/nvi/",
        ),
    )
