import asyncio

from starlette.types import Message, Receive, Scope, Send

from app.request_body_limit import RequestBodyLimitMiddleware


def test_passes_a_non_http_scope_through_untouched() -> None:
    seen: list[Receive] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(receive)

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        return None

    asyncio.run(RequestBodyLimitMiddleware(app, max_bytes=1)({"type": "lifespan"}, receive, send))

    assert seen == [receive]
