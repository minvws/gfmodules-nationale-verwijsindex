from pathlib import Path
from unittest.mock import mock_open, patch

from app.config import get_config


def test_load_default_uvicorn_parmas():
    data = """
    [uvicorn]
    # If true, the api docs will be enabled
    swagger_enabled = True
    # Endpoint for swagger api docs
    docs_url = /docs
    # Endpoint for redoc api docs
    redoc_url = /redocs
    # Host for the uvicorn server
    host = 0.0.0.0
    # Port for the uvicorn server
    port = 8501
    # Live reload for uvicorn server
    reload = True

    # SSL configuration
    use_ssl = False
    ssl_base_dir = secrets/ssl
    ssl_cert_file = server.cert
    ssl_key_file = server.key
    """

    with patch("builtins.open", mock_open(read_data=data)) as mock_file:
        config = get_config()

    assert config is not None
    mock_file.assert_called_with(Path(__file__), encoding="locale")
