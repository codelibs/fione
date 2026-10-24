"""Python modules (global, not per project): the list for everyone signed in; upload and
delete for administrators, as in the API. Uploaded modules are not sandboxed: they run in
job workers with the application's privileges, which every page about them says, and an
upload needs the administrator's explicit acknowledgement (checked on the server)."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from fione.api.deps import Auth, Conn, cookie_auth, request_host
from fione.api.downloads import tmp_dir
from fione.api.security import origin_matches, tokens_equal
from fione.auth.roles import Role
from fione.modules import service as modules
from fione.modules.registry import MODULE_ID, redact
from fione.modules.service import MAX_SOURCE_BYTES, ModuleNotFound
from fione.web.automl import Posted, _text
from fione.web.uploads import UploadFormError, read_form, size_text
from fione.web.views import UiError, action_auth, render

router = APIRouter(include_in_schema=False)


def _signed_in(request: Request, conn) -> Auth:
    auth = cookie_auth(request, conn)
    if auth is None:
        raise UiError(401, "error.session")
    return auth


def _admin(auth: Auth) -> Auth:
    if auth.user.role != Role.ADMIN:
        raise UiError(403, "error.admin_only")
    return auth


def _size(request: Request, module_id: str) -> str | None:
    try:
        return size_text(request.app.state.storage.size(modules.module_key(module_id)))
    except (KeyError, ValueError):  # the file is gone, or an id storage refuses
        return None


@router.get("/modules")
def modules_page(request: Request, conn: Conn) -> Response:
    auth = _signed_in(request, conn)
    listed = modules.list_modules(conn)
    uploaded = modules.uploaded_at(conn)
    rows = [
        {
            "info": m,
            "uploaded": uploaded.get(m.id),
            "size": None if m.builtin else _size(request, m.id),
        }
        for m in listed
    ]
    admin = auth.user.role == Role.ADMIN
    return render(request, "modules.html", auth, rows=rows, admin=admin)


def _upload_view(
    request: Request, auth: Auth, *, status=200, error=None, detail=None, module_id=""
):
    return render(
        request,
        "module_upload.html",
        auth,
        status=status,
        error=error,
        detail=detail,
        module_id=module_id,
        max_kb=MAX_SOURCE_BYTES // 1024,
        pattern=MODULE_ID.pattern,
    )


@router.get("/modules/upload")
def upload_page(request: Request, conn: Conn) -> Response:
    return _upload_view(request, _admin(_signed_in(request, conn)))


@router.post("/modules/upload")
async def upload(request: Request, conn: Conn) -> Response:
    """Admin, Origin, then the form; the acknowledgement and the CSRF token are checked
    before the module is stored (its metadata is read in a separate process)."""
    auth = _admin(_signed_in(request, conn))
    if not origin_matches(request.headers.get("origin"), request_host(request)):
        raise UiError(403, "error.forbidden")
    try:
        form = await read_form(request, tmp_dir(request.app.state.settings), max_fields=3)
    except UploadFormError:
        return _upload_view(request, auth, status=400, error="upload.error.form")
    try:
        token = form.get("csrf_token")
        if not tokens_equal(auth.session.csrf, token if isinstance(token, str) else None):
            raise UiError(403, "error.csrf")
        module_id = form.get("id")
        module_id = module_id.strip() if isinstance(module_id, str) else ""
        if form.get("acknowledge") != "yes":
            return _upload_view(
                request, auth, status=422, error="modules.error.acknowledge", module_id=module_id
            )
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not upload.filename:
            return _upload_view(
                request, auth, status=422, error="modules.error.file", module_id=module_id
            )
        source = await upload.read(MAX_SOURCE_BYTES + 1)  # the service refuses anything longer

        def run():
            return modules.upload_module(
                conn, request.app.state.storage, auth.user, module_id, source
            )

        try:
            await run_in_threadpool(run)
        except ValueError as e:  # ModuleError and the service's other refusals
            return _upload_view(
                request,
                auth,
                status=422,
                error="modules.error.refused",
                detail=redact(str(e)),
                module_id=module_id,
            )
    finally:
        await form.close()
    return RedirectResponse("/modules", 303)


@router.post("/modules/{module_id}/delete")
def delete(request: Request, conn: Conn, module_id: str, form: Posted) -> Response:
    auth = _admin(action_auth(request, conn, _text(form, "csrf_token")))
    if not MODULE_ID.fullmatch(module_id):
        raise UiError(404, "error.not_found")
    try:
        modules.delete_module(conn, request.app.state.storage, auth.user, module_id)
    except ModuleNotFound:
        raise UiError(404, "error.not_found") from None
    except ValueError:  # a built-in module, or not a module id
        raise UiError(422, "modules.error.builtin") from None
    return RedirectResponse("/modules", 303)
