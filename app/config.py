import configparser
import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


_PATH = "app.conf"
_ENVIRONMENT_CONFIG_PATH_NAME = "FASTAPI_CONFIG_PATH"
_CONFIG = None


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class ConfigApp(BaseModel):
    loglevel: LogLevel = Field(default=LogLevel.info)
    provider_id: str


class ConfigDeziRegister(BaseModel):
    uzi_server_certificate_ca_cert_path: str
    dezi_register_trusted_signing_certs_store_path: str


class ConfigUraMiddleware(BaseModel):
    override_authentication_ura: str | None = Field(default=None)
    use_authentication_ura_allowlist: bool = Field(default=True)
    allowlist_cache_in_seconds: int = Field(default=30)


class ConfigDatabase(BaseModel):
    dsn: str
    create_tables: bool = Field(default=False)
    retry_backoff: list[float] = Field(default=[0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 4.8, 6.4, 10.0])
    pool_size: int = Field(default=5, ge=0, lt=100)
    max_overflow: int = Field(default=10, ge=0, lt=100)
    pool_pre_ping: bool = Field(default=False)
    pool_recycle: int = Field(default=3600, ge=0)


class ConfigPseudonymApi(BaseModel):
    endpoint: str
    timeout: int = Field(default=30, gt=0)
    mtls_cert: str
    mtls_key: str
    verify_ca: str | bool = Field(default=True)


class ConfigUvicorn(BaseModel):
    swagger_enabled: bool = Field(default=False)
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8502, gt=0, lt=65535)
    reload: bool = Field(default=True)
    reload_delay: float = Field(default=1)
    reload_dirs: list[str] = Field(default=["app"])
    use_ssl: bool = Field(default=False)
    ssl_base_dir: str | None
    ssl_cert_file: str | None
    ssl_key_file: str | None


class ConfigTelemetry(BaseModel):
    enabled: bool = Field(default=False)
    endpoint: str | None
    service_name: str | None
    tracer_name: str | None


class ConfigStats(BaseModel):
    enabled: bool = Field(default=False)
    host: str | None
    port: int | None
    module_name: str | None


class ConfigClientOAuth(BaseModel):
    enabled: bool = Field(default=False)
    override_ura_number: str | None = Field(default=None)
    jwks_url: str
    issuer: str
    audience: str


class Config(BaseModel):
    app: ConfigApp
    database: ConfigDatabase
    pseudonym_api: ConfigPseudonymApi
    telemetry: ConfigTelemetry
    stats: ConfigStats
    dezi_register: ConfigDeziRegister
    uvicorn: ConfigUvicorn
    client_oauth: ConfigClientOAuth


def read_ini_file(path: str) -> Any:
    ini_data = configparser.ConfigParser()
    ini_data.read(path)

    ret = {}
    for section in ini_data.sections():
        ret[section] = dict(ini_data[section])
        remove_empty_values(ret[section])
    return ret


def remove_empty_values(section: dict[str, Any]) -> None:
    for key in list(section.keys()):
        if section[key] == "":
            del section[key]


def reset_config() -> None:
    global _CONFIG
    _CONFIG = None


def set_config(config: Config) -> None:
    global _CONFIG
    _CONFIG = config


def get_config(path: str | None = None) -> Config:
    global _CONFIG
    global _PATH

    if _CONFIG is not None:
        return _CONFIG

    if path is None:
        path = os.environ.get(_ENVIRONMENT_CONFIG_PATH_NAME) or _PATH

    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    ini_data = read_ini_file(path)

    try:
        # Convert database.retry_backoff to a list of floats
        if (
            "database" in ini_data
            and "retry_backoff" in ini_data["database"]
            and isinstance(ini_data["database"]["retry_backoff"], str)
        ):
            # convert the string to a list of floats
            ini_data["database"]["retry_backoff"] = [float(i) for i in ini_data["database"]["retry_backoff"].split(",")]

        _CONFIG = Config.model_validate(ini_data)
    except ValidationError as e:
        raise e

    return _CONFIG
