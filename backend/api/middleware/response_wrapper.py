"""
Response Wrapper Middleware

Wraps JSON responses on /api/v1/* routes:
  - 2xx → {"success": true, ...body}
  - 4xx/5xx → {"success": false, "error": "message"}

Non-JSON responses pass through unchanged.
Temporary — will be removed when the frontend is refactored.
"""

import json
from collections.abc import MutableMapping
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ResponseWrapperMiddleware:
    def __init__(self, app: ASGIApp, path_prefix: str = "/api/v1") -> None:
        self.app = app
        self.path_prefix = path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if not path.startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return

        status_code: int = 200
        response_headers: MutableMapping[str, str] = {}
        body_parts: list[bytes] = []
        is_json = False
        initial_message: Message | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_headers, is_json, initial_message

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                content_type = headers.get("content-type", "")
                is_json = "application/json" in content_type

                if not is_json:
                    await send(message)
                    return

                initial_message = message
                return

            if message["type"] == "http.response.body":
                if not is_json:
                    await send(message)
                    return

                body_parts.append(message.get("body", b""))
                more_body = message.get("more_body", False)

                if more_body:
                    return

                raw_body = b"".join(body_parts)
                wrapped = _wrap_body(raw_body, status_code)
                encoded = json.dumps(wrapped, default=str).encode()

                if initial_message is None:  # pragma: no cover — defensive guard
                    return
                headers = MutableHeaders(scope=initial_message)
                headers["content-length"] = str(len(encoded))

                await send(initial_message)
                await send({"type": "http.response.body", "body": encoded})

        await self.app(scope, receive, send_wrapper)


def _wrap_body(raw_body: bytes, status_code: int) -> dict[str, Any]:
    try:
        body: Any = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}

    if 200 <= status_code < 300:
        if isinstance(body, dict):
            return {"success": True, **body}
        return {"success": True, "data": body}

    error_msg: str = "An error occurred"
    if isinstance(body, dict):
        detail = body.get("detail", body.get("message", error_msg))
        error_msg = str(detail)
    return {"success": False, "error": error_msg}
