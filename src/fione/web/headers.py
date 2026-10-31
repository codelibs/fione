"""Security headers for everything outside the API: pages, redirects and static files.

Pages get a strict Content-Security-Policy (no inline scripts or styles, no framing) and are
never cached, since they carry per-user data and the CSRF token. Static files may be cached.
API responses (``/api/...``, including the OpenAPI docs page) are left as they are.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def ui_headers(headers: MutableHeaders, *, page: bool = True) -> None:
    """Set the UI's security headers; ``page``: also the CSP and ``no-store``. Also used for
    responses sent from outside this middleware (the HTML 500 page)."""
    headers["X-Content-Type-Options"] = "nosniff"
    headers["Referrer-Policy"] = "same-origin"
    if page:
        headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        headers["Cache-Control"] = "no-store"


class UIHeaders:
    def __init__(self, app: ASGIApp, *, static_prefix: str = "/static/"):
        self.app = app
        self.static_prefix = static_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or path == "/api" or path.startswith("/api/"):
            await self.app(scope, receive, send)
            return
        page = not path.startswith(self.static_prefix)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                ui_headers(MutableHeaders(scope=message), page=page)
            await send(message)

        await self.app(scope, receive, send_with_headers)
