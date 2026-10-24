"""The FastAPI application: state, lifespan, body limits, error handlers and routers.

A new router is one more entry in ``ROUTERS``; a route that accepts uploads also adds its
path pattern to ``UPLOAD_PATHS`` (other requests are limited to ``MAX_BODY_BYTES``).
"""

import logging
import re
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from fione import db
from fione.api import routes_auth, routes_datasets, routes_projects, routes_system, routes_users
from fione.api.errors import error_response, install_error_handlers
from fione.api.security import LoginThrottle, SessionSigner, ensure_setup_token
from fione.auth import service as auth_service
from fione.config import Settings, get_settings, load_secret
from fione.jobs.runner import JobRunner
from fione.storage import open_storage
from fione.version import __version__

API_PREFIX = "/api/v1"
DB_FILE = "fione.db"
MAX_BODY_BYTES = 1 << 20
# Multipart framing around the file: the file itself is checked against max_upload_bytes.
UPLOAD_SLACK_BYTES = 1 << 20

ROUTERS = [
    routes_system.router,
    routes_auth.router,
    routes_users.router,
    routes_projects.router,
    routes_datasets.router,
]
UPLOAD_PATHS = [re.compile(rf"^{API_PREFIX}/projects/[^/]+/datasets$")]

setup_log = logging.getLogger("fione.setup")


class BodyLimit:
    """Refuse request bodies over the limit (413) before they are buffered or spooled.

    FastAPI reads a declared body before it runs dependencies, so this bound applies even to
    requests that authentication will reject. A declared ``Content-Length`` is checked up
    front; the bytes actually received are counted too (chunked bodies, lying headers).
    """

    def __init__(self, app: ASGIApp, upload_limit: int):
        self.app = app
        self.upload_limit = upload_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        upload = scope["method"] == "POST" and any(p.match(scope["path"]) for p in UPLOAD_PATHS)
        limit = self.upload_limit if upload else MAX_BODY_BYTES
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > limit):
            status, code = (413, "too_large") if declared.isdigit() else (400, "bad_request")
            response = error_response(status, code, "request body too large or malformed")
            await response(scope, receive, send)
            return
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise HTTPException(413, "request body too large")
            return message

        await self.app(scope, limited_receive, send)


def _announce_setup(settings: Settings, db_path) -> None:
    with closing(db.connect(db_path)) as conn:
        db.migrate(conn)
        if not auth_service.needs_first_admin(conn):
            return
    token, generated = ensure_setup_token(settings)
    if generated:
        setup_log.warning("No administrator exists. Setup token: %s", token)
    else:
        setup_log.warning("No administrator exists. Use the setup token from FIONE_SETUP_TOKEN.")


def create_app(settings: Settings | None = None, *, start_runner: bool | None = None) -> FastAPI:
    settings = settings or get_settings()
    run_jobs = settings.runner_enabled if start_runner is None else start_runner
    db_path = settings.data_dir / DB_FILE

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _announce_setup(settings, db_path)
        auth_service.warm_up()
        runner = None
        if run_jobs:
            runner = JobRunner(settings, db_path)
            runner.recover_orphans()
            runner.start()
        app.state.runner = runner
        try:
            yield
        finally:
            if runner is not None:
                runner.stop()

    app = FastAPI(
        title="Fione",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    secret = load_secret(settings)
    app.state.settings = settings
    app.state.db_path = db_path
    app.state.storage = open_storage(settings)
    app.state.secret = secret
    app.state.runner = None
    app.state.signer = SessionSigner(secret, settings.session_max_age_secs)
    app.state.throttle = LoginThrottle(settings.login_max_failures, settings.login_window_secs)
    install_error_handlers(app)
    app.add_middleware(BodyLimit, upload_limit=settings.max_upload_bytes + UPLOAD_SLACK_BYTES)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    return app
