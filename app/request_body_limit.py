from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.exceptions import RequestTooLargeError


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                raise RequestTooLargeError(f"Request body exceeds the maximum of {self.max_bytes} bytes")
            return message

        await self.app(scope, limited_receive, send)
