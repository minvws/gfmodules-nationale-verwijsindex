import logging

from app.models.token import AccessToken
from app.services.oauth_token_client import OAuthTokenClient

logger = logging.getLogger(__name__)


class OAuthTokenClientMock(OAuthTokenClient):
    def __init__(self) -> None:
        self._tokens = []

    def fetch_token(self, scope: str, target_audience: str) -> AccessToken:
        logger.debug("Returning mocked token because OAuthTokenClientMock is enabled")
        return AccessToken(
            access_token="mock_token",
            token_type="Bearer",
            scope=scope,
            refresh_token="mock_refresh_token",
        )
