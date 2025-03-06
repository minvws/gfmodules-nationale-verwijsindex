from app.services.authorization_services.authorization_interface import BaseAuthService


class StubAuthService(BaseAuthService):
    def is_authorized(self, **kwargs: bool | str) -> bool:
        return True
