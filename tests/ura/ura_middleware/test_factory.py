from app.config import ConfigUraMiddleware
from app.db.db import Database
from app.ura.ura_middleware.config_based_ura_middleware import ConfigBasedUraMiddleware
from app.ura.ura_middleware.factory import create_ura_middleware
from app.ura.ura_middleware.request_ura_middleware import RequestUraMiddleware


def test_create_ura_middleware_should_return_config_based_ura(
    database: Database,
) -> None:
    config = ConfigUraMiddleware(override_authentication_ura="123456", use_authentication_ura_allowlist=False)

    middleware = create_ura_middleware(config, database)

    assert isinstance(middleware, ConfigBasedUraMiddleware)
    assert middleware.filter_service is None


def test_create_ura_middleare_should_return_config_based_ura_with_filter_service(
    database: Database,
) -> None:
    config = ConfigUraMiddleware(override_authentication_ura="123456", use_authentication_ura_allowlist=True)
    middleware = create_ura_middleware(config, database)

    assert isinstance(middleware, ConfigBasedUraMiddleware)
    assert middleware.filter_service is not None


def test_create_ura_middleware_should_return_request_ura_middleware(
    database: Database,
) -> None:
    config = ConfigUraMiddleware(override_authentication_ura=None, use_authentication_ura_allowlist=False)

    middleware = create_ura_middleware(config, database)

    assert isinstance(middleware, RequestUraMiddleware)
    assert middleware.filter_service is None


def test_create_ura_middleware_should_return_request_ura_middleware_with_filter_service(
    database: Database,
) -> None:
    config = ConfigUraMiddleware(override_authentication_ura=None, use_authentication_ura_allowlist=True)

    middleware = create_ura_middleware(config, database)

    assert isinstance(middleware, RequestUraMiddleware)
    assert middleware.filter_service is not None
