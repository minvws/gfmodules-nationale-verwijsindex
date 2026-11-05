from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLargeError(HTTPException):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(status_code=413, detail=f"Request body exceeds the maximum of {max_bytes} bytes")

    def __str__(self) -> str:
        return self.detail


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                raise RequestBodyTooLargeError(self.max_bytes)
            return message

        await self.app(scope, limited_receive, send)
