"""Security headers for everything outside the API: pages, redirects and static files.

Pages get a strict Content-Security-Policy (no inline scripts or styles, no framing) and are
never cached, since they carry per-user data and the CSRF token. Static files may be cached.
API responses (``/api/...``, including the OpenAPI docs page) are left as they are.

A view that frames another origin (the notebook page) sets ``request.state.csp_frame_src``
to it; that response alone gets ``frame-src <origin>``. A view may also set
``request.state.referrer_policy`` for its response alone (the notebook page sends its origin
to the notebook gateway, whose sign-in checks it).
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
                headers = MutableHeaders(scope=message)
                ui_headers(headers, page=page)
                # Read now: the view has run (``request.state`` is ``scope["state"]``).
                state = scope.get("state") or {}
                frame_src = state.get("csp_frame_src")
                if page and frame_src:
                    headers["Content-Security-Policy"] += f"; frame-src {frame_src}"
                if page and state.get("referrer_policy"):
                    headers["Referrer-Policy"] = state["referrer_policy"]
            await send(message)

        await self.app(scope, receive, send_with_headers)
