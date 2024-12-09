import configparser
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_INI_FILE = PROJECT_ROOT / "app.conf"


NVI_APPCONFIG_FILEPATH_ENV_KEY = "NVI_APPCONFIG_FILEPATH"


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class ConfigApp(BaseModel):
    loglevel: LogLevel = Field(default=LogLevel.info)
    provider_id: str
    override_authentication_ura: str | None
    swagger_enabled: bool = Field(default=False)
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")


class ConfigDatabase(BaseModel):
    dsn: str
    create_tables: bool = Field(default=False)
    retry_backoff: list[float] = Field(
        default=[0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 4.8, 6.4, 10.0]
    )
    pool_size: int = Field(default=5, ge=0, lt=100)
    max_overflow: int = Field(default=10, ge=0, lt=100)
    pool_pre_ping: bool = Field(default=False)
    pool_recycle: int = Field(default=3600, ge=0)


class ConfigPseudonymApi(BaseModel):
    mock: bool = Field(default=False)
    endpoint: str
    timeout: int = Field(default=30, gt=0)
    mtls_cert: str | None = Field(default=None)
    mtls_key: str | None = Field(default=None)
    mtls_ca: str | None = Field(default=None)


class ConfigUvicorn(BaseModel):
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


class Config(BaseModel):
    app: ConfigApp
    database: ConfigDatabase
    pseudonym_api: ConfigPseudonymApi
    telemetry: ConfigTelemetry
    stats: ConfigStats


def read_ini_file(path: Path) -> Any:
    ini_data = configparser.ConfigParser()
    ini_data.read(path)

    ret = {}
    for section in ini_data.sections():
        ret[section] = dict(ini_data[section])

    return ret


def load_default_config(path: Path = DEFAULT_CONFIG_INI_FILE) -> Config:
    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    ini_data = read_ini_file(path)

    try:
        # Convert database.retry_backoff to a list of floats
        if "retry_backoff" in ini_data["database"] and isinstance(
            ini_data["database"]["retry_backoff"], str
        ):
            # convert the string to a list of floats
            ini_data["database"]["retry_backoff"] = [
                float(i) for i in ini_data["database"]["retry_backoff"].split(",")
            ]

        config = Config(**ini_data)
    except ValidationError as e:
        raise e

    return config


def load_default_uvicorn_config(path: Path) -> ConfigUvicorn:
    # To be inline with other python code, we use INI-type files for configuration. Since this isn't
    # a standard format for pydantic, we need to do some manual parsing first.
    data: dict[str, Any] = read_ini_file(path)
    section_data = data.get("uvicorn")

    if not section_data:
        raise ValidationError
    try:
        config = ConfigUvicorn(**section_data)
    except ValidationError as e:
        raise e

    return config
