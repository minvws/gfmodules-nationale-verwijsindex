from typing import Any

import uvicorn

from app.config import (
    DEFAULT_CONFIG_INI_FILE,
    ConfigUvicorn,
    load_default_uvicorn_config,
)


def _format_uvicorn_params(config: ConfigUvicorn) -> dict[str, Any]:
    kwargs = {
        "host": config.host,
        "port": config.port,
        "reload": config.reload,
        "reload_delay": config.reload_delay,
        "reload_dirs": config.reload_dirs,
    }
    if (
        config.use_ssl
        and config.ssl_base_dir is not None
        and config.ssl_cert_file is not None
        and config.ssl_key_file is not None
    ):
        kwargs["ssl_keyfile"] = config.ssl_base_dir + "/" + config.ssl_key_file
        kwargs["ssl_certfile"] = config.ssl_base_dir + "/" + config.ssl_cert_file
    return kwargs


def main() -> None:
    uvicorn_config = load_default_uvicorn_config(
        DEFAULT_CONFIG_INI_FILE,
    )
    formatted_params = _format_uvicorn_params(uvicorn_config)

    uvicorn.run(
        "app.application:create_fastapi_app",
        **formatted_params,
    )


if __name__ == "__main__":
    main()
