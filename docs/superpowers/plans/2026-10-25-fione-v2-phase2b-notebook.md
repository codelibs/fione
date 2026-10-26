# Fione v2 Phase 2b (fione-sdk and embedded JupyterLab) Implementation Plan

> Work through the plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `fione-sdk` (a Python client of the Fione API, usable from any Jupyter) and an opt-in, per-user JupyterLab embedded in the Fione UI and signed in through Fione, with the three-layer boundary of spec 6.5.

**Architecture:** Fione issues scoped, expiring API tokens and one-time launch tokens. A tiny stdlib `notebook-launcher` service, which alone holds the Docker socket, starts one hardened container per user from a pinned notebook image. Inside that image, a Jupyter Server extension (`fione_notebook`) turns a launch token into a login cookie and authorizes only the container's owner. An nginx `notebook-gateway` on a separate same-site origin proxies browsers to the containers. It also relays the containers' SDK calls to Fione, which is the only path from a container to Fione. Everything new is in the Compose profile `notebook`. Without it, Fione behaves as in Phase 1.

**Tech Stack:** Python 3.12, FastAPI, Jinja2 + HTMX, SQLite, httpx + pandas (SDK), jupyter_server 2.21.x, jupyterlab 4.6.x, tornado 6.5.x, ipykernel, Python stdlib `http.server`/`http.client` (launcher), nginx (unprivileged image), Docker Engine API, Docker Compose profiles, pytest, Playwright, uv.

**Spec:** `docs/superpowers/specs/2026-10-24-fione-v2-design.md` (6.5; 4.4 roles; 4.6 licences; 10.5 tests).

## Global Constraints

Rulings (decisions already made; the reason follows each):
- **Topology.** The nginx gateway has an origin of its own that is same-site with Fione: port 8888 locally, a sibling subdomain in production. Fione's CSP adds `frame-src <notebook origin>` on the notebook page only. Jupyter's CSP is `frame-ancestors 'self' <fione origin>`. Jupyter is never served from Fione's origin. Reasons: notebook output JavaScript running on Fione's origin would be XSS against Fione and would bypass token scopes. A cross-site iframe loses the Lax login cookie (verified in a browser). `'self'` stays in Jupyter's `frame-ancestors` because that is the verified form.
- **Auth.** Fione issues a one-time launch token that lives 60 s, signed with a per-container key; Fione's own secret never enters a container. A custom Jupyter IdentityProvider, LoginHandler and Authorizer live in the package `fione_notebook`. `allow_unauthenticated_access=False`. The launch token is scrubbed from every log. Cookie requests are never marked token-authenticated. JupyterLab's settings and workspaces APIs bypass the Authorizer, so they are blocked at the gateway or in tornado settings. Reasons: Jupyter skips XSRF, Origin and CORS checks for token-authenticated requests, and user code can read anything the container holds.
- **Permissions.** `users.notebook` is `none|run`, default `none`, implicit for admins, and `none` for viewers unless granted. There is no read-only "view" mode. Jupyter's resources are per container, not per project, so project access is enforced **only** by the user's scoped Fione token inside the container. An admin's notebook token is capped at editor power. Reason: kernel code would otherwise hold admin power (module upload and model import run code on the Fione host).
- **Tokens.** `api_tokens` gains `expires_at` and `scope` (`full|notebook`) in an append-only migration. Scope `notebook` is checked against an allow-list of routes; tokens, users, password, module upload/delete, model import and `/auth/*` are not on it. An expired token gets 401. A token created by a bearer request inherits the caller's scope, and its expiry is no later than the caller's. Reason: today any bearer token can mint a permanent token.
- **Launching.** The stdlib `notebook-launcher` holds the Docker socket, in the opt-in profile `notebook`; Fione never holds it. The container spec is fixed:
  - CPU 2, memory 4 GiB with no swap, 512 pids.
  - `CapDrop ALL`, `no-new-privileges`, user `1000:1000`, `Init`, `AutoRemove`.
  - Labels `fione.notebook=1`, `fione.project=<compose project>`, `fione.uid`, `fione.expires`. A per-user named volume for the notebooks.
  - Network: only the internal network `notebooks`.
  
  Kernels are culled after 30 min idle, the server after 1 h. There is no egress, so no `pip install`. `fione` must not join `notebooks`. Containers reach the API only through the gateway relay, which requires `Bearer` and refuses `/api/v1/auth`, `/api/v1/tokens` and `/api/v1/users`. Reasons: the socket is root-equivalent on the host, and Fione runs admin-uploaded code unsandboxed. A container that reached `fione:8080` directly could spoof `X-Forwarded-For` and brute-force logins.
- **fione-sdk.** A separate distributable under `sdk/` (distribution `fione-sdk`, import `fione_sdk`), depending on httpx and pandas only, version `20.0.0` like Fione. It covers datasets, jobs (train/wait/events/cancel), leaderboard, `predict(df)` (upload + batch-predict + download) and `run_module` (the module job API). Modules are **not** imported locally: they run server side.
- **Licences.**
  - `scripts/check_licenses.py` `EXCEPTIONS` gains `certifi` and `fqdn` (MPL-2.0).
  - JupyterLab's bundled elkjs (EPL-2.0) and FontAwesome (CC-BY-4.0 AND OFL-1.1 AND MIT) ship only in the opt-in notebook image. They come from PyPI at build time and are **not vendored into the repository**. **The maintainer confirms this in the PR description.**
- **Notebook image.** `docker/Dockerfile.notebook` with pinned versions: jupyter_server 2.21.x (2.21.1), jupyterlab 4.6.x (4.6.4), tornado 6.5.x (`>=6.5,<6.6`; 6.6 is under two weeks old). The release workflow publishes it, and the launcher image, on version tags only, with SHA-pinned actions as before.
- **Version and docs.** The version stays `20.0.0`. Docs: README (en/ja) sections, known limitations (the launcher's Docker socket is host-root-equivalent; opt-in), `configuration.md`, and a notebook quickstart (en/ja).

Plan decisions (made by this plan, not by the rulings; the reason follows each):
- **Derived per-container key.** The key is `HMAC-SHA256(install secret, "fione-notebook-launch-v1:<uid>:<nonce>")`, with a fresh nonce per start, stored in `notebook_sessions`. HMAC is one-way, so the key reveals nothing about the install secret, and no key is kept at rest.
- **Settings and workspaces are blocked at the gateway.** It refuses their write methods; `GET` stays allowed so JupyterLab can boot. Cost: layout and settings changes are not saved across reloads. **The maintainer confirms this in the PR description.** If JupyterLab shows a blocking error because of it (Task 10 checks), stop and report; never quietly allow the writes.
- **Launcher network.** The launcher talks to Fione on a network of its own, `launcher`, not `backend`: SeaweedFS's ports on `backend` have no credentials. The launcher is the boundary: it accepts only a digits-only uid and fixed-format values, and it takes the image from its own configuration.
- **One lifetime.** `FIONE_NOTEBOOK_MAX_LIFETIME_SECS` (default 43200, 12 h, at most 604800 like the launcher's bound) is the notebook token's expiry, the Jupyter cookie's max-age and the launcher's maximum container age.
- **Scope check as an allow-list.** Notebook tokens are checked against an explicit allow-list of routes, so a new route is refused until someone classifies it. The deny-list of ruling 4 is its complement.
- **Nothing user-writable is served or loaded by Jupyter.** Every user's Jupyter shares the notebook origin, and a path is not a browser security boundary. Any unsandboxed HTML a user could get served under `/user/<uid>/`, for example through the unauthenticated lab-extension static handler, which searches the user data dir, would run on that shared origin. From there it could take over another signed-in user's JupyterLab, and with it their `FIONE_TOKEN`. So the image sets `JUPYTER_CONFIG_DIR` and `JUPYTER_DATA_DIR` to root-owned directories in the image, and `JUPYTER_PATH` stays unset. The residual risk, and per-user notebook subdomains as the real fix, is an open decision for the maintainer (see Self-Review Notes).

Conventions (Phase 1, apply to every task):
- Work on branch `v2-phase2b`. Commit messages are public-safe implementation summaries with no attribution lines, written to a file and committed with `git commit -F <file>`.
- No local paths, usernames or private URLs in any committed file.
- Migrations are appended to `fione.db.MIGRATIONS`; earlier ones are never edited. Phase 2a's migrations are already in the base; never rely on a migration's index in tests (find it by content, as `tests/unit/test_db.py` does).
- Authorization changes get matrix tests (`tests/api/test_permissions.py` style).
  - UI form posts check `Origin` and the session CSRF token (`web/access.py` `form_auth` / `action_auth`).
  - API cookie requests need `X-CSRF-Token`.
  - Every rendered value is autoescaped, and launcher- or Jupyter-provided text is never rendered.
  - No inline scripts or styles (the strict CSP).
- Every i18n key exists in `en.json` and `ja.json`. UI changes update `scripts/ui-screenshots.py` and are reviewed in light/dark, en/ja, phone/desktop.
- Every new `FIONE_*` setting or compose variable gets its `docs/configuration.md` row **in the same commit**: `tests/unit/test_docs.py` requires set equality and rejects unknown names on any page.
- Test file basenames must be unique across `tests/` (there are no `__init__.py` files, so a clash aborts collection). Test helpers live in `tests/api_helpers.py` (`add_user`, `bearer`, `iris_frame`, `FAST_CONFIG`, `make_settings`).
- Pytest markers: `docker` (needs a Docker daemon) and `notebook` (needs the `notebook` dependency group) are deselected by default like `e2e`. CI runs them explicitly (Tasks 5, 9, 10).
- Keep machine load low: run only the named test files while iterating, and build images only in the tasks that need them.

## Review Focus

These are the security failure modes most likely to hurt a real installation. Each one has a pinned test in the task that owns the code.
1. **Relay deny-list bypass / SSRF.** Paths like `/api/v1/%74okens`, `/api/v1/projects/..%2F..%2Ftokens`, `/api/v1//users`, `/api/v1/./auth/login`, `/API/V1/TOKENS` and `/api/v1/tokens/` must give 403/404, with the upstream never seeing them. No path may make the gateway proxy anywhere except `fione:8080` (relay) or `nb-<digits>:8888` (Task 9).
2. **Token scope bypass.**
   - A notebook token must not reach any route off the allow-list, mint a full or longer-lived token, or act as an admin.
   - A token expired 1 s ago gets 401; one valid for 60 more seconds gets 200.
   - Every `/api/v1` route must be classified, so a new one cannot slip through (Task 1).
3. **Cookie/XSRF handling.**
   - `?token=` and `Authorization: token` are ignored by Jupyter.
   - A cookie POST without `_xsrf` gets 403, and a WebSocket with a foreign `Origin` gets 403.
   - `fione_session` never reaches a container, and the Jupyter cookie is `HttpOnly; SameSite=Lax; Path=/user/<uid>/` (Tasks 5, 9).
4. **Docker socket exposure.**
   - Only the launcher mounts the socket, it publishes no port, and it is not on `notebooks`.
   - Malformed launcher input (a non-digit uid, a newline in a value, a foreign image) gets 422 before any Docker call.
   - The container create body equals the fixed spec exactly, with no `Binds`, `Privileged`, `PortBindings`, `CapAdd` or `Devices` (Tasks 7, 9).
5. **Log leaks.** The launch token is absent from Jupyter's log, the gateway's access and error logs and Fione's log. The notebook token is absent from Fione's and the launcher's logs (Tasks 5, 7, 8, 9).
6. **Egress.** From a cell: `pypi.org`, `1.1.1.1`, `host.docker.internal`, `fione`, `seaweedfs` and other users' containers' Jupyter refuse or fail. Only the relay answers, and only with a bearer token (Tasks 7, 10).
7. **Cross-user script on the shared notebook origin.**
   - An HTML or JS file a user writes under their home or data dir is never served.
   - `/files/*` and nbconvert HTML carry `sandbox allow-scripts`.
   - No response under `/user/<uid>/` serves user-controlled HTML without `sandbox` (Tasks 5, 6).

---

## File Structure

```
src/fione/auth/{tokens,service,roles}.py        # TokenScope, expiry, notebook permission (Tasks 1, 4)
src/fione/api/{deps,routes_users,schemas}.py    # scope enforcement, inherited scope, notebook field
src/fione/notebooks/{__init__,launch,launcher,service}.py   # launch tokens, launcher client, sessions (Task 8)
src/fione/web/{notebook_ui,headers,admin_ui,account_ui}.py + templates/{notebook,_notebook_status}.html
src/fione_notebook/{__init__,auth,config}.py    # the Jupyter Server extension (Task 5)
src/fione_launcher/{__init__,__main__,config,docker,spec,server}.py   # stdlib launcher (Task 7)
sdk/{pyproject.toml,README.md,src/fione_sdk/{__init__,client,jobs,errors}.py}   # Tasks 2-3
docker/{Dockerfile.notebook,Dockerfile.launcher,notebook-gateway.conf}
docker/notebook/{jupyter_server_config.py,page_config.json}
docker/{compose.yaml,compose.e2e.yaml,.env.example,e2e.env}
tests/{api/test_token_scope.py, sdk/, notebook/, launcher/, docker/, unit/test_compose.py, e2e/test_notebook.py}
docs/{notebook.md,notebook.ja.md,configuration.md,known-limitations.md}, README.md, README.ja.md
```

---

### Task 1: Token scope and expiry

**Files:**
- Modify: `src/fione/db.py` (append a migration), `src/fione/auth/tokens.py`, `src/fione/auth/service.py`, `src/fione/api/deps.py`, `src/fione/api/routes_users.py`, `src/fione/api/schemas.py`
- Modify: `src/fione/web/account_ui.py`, `src/fione/web/templates/account.html`, `src/fione/i18n/{en,ja}.json`, `docs/known-limitations.md`
- Test: `tests/api/test_token_scope.py`, `tests/unit/test_auth.py`

**Interfaces:**
- Produces:
  - `TokenScope(StrEnum)`: `FULL = "full"`, `NOTEBOOK = "notebook"` in `fione.auth.tokens`.
  - Migration: `ALTER TABLE api_tokens ADD COLUMN expires_at TEXT` and `ADD COLUMN scope TEXT NOT NULL DEFAULT 'full' CHECK (scope IN ('full','notebook'))`.
  - `expires_at` is always the UTC text `YYYY-MM-DD HH:MM:SS`, the format of `CURRENT_TIMESTAMP`, so the comparison in SQL is a correct string comparison.
- Produces:
  - `service.expiry_after(seconds: int) -> str`: UTC in that format.
  - `ApiToken` gains `scope: TokenScope` and `expires_at: str | None`.
  - `service.create_token(conn, user_id: int, name: str, *, scope: TokenScope = TokenScope.FULL, expires_at: str | None = None) -> tuple[ApiToken, str]`. An `expires_at` that does not match `^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$` raises `ValueError`.
  - `service.token_identity(conn, token: str) -> tuple[User, ApiToken] | None`: none if revoked or expired (`expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP`). `user_from_token` stays as a wrapper.
- Produces:
  - `Auth` gains `scope: TokenScope = TokenScope.FULL` and `token: ApiToken | None = None`.
  - In `get_auth`, a notebook-scope bearer request whose route is not in `NOTEBOOK_SCOPE_ROUTES` gets `ApiError(403, "token_scope", "this token cannot be used here")`. The set is a `frozenset[tuple[str, str]]` of (method, route path template **without** the `/api/v1` prefix, as `request.scope["route"].path` holds it) in `deps.py`. A request with no `scope["route"]` is denied.
  - When the token's user is an admin, `Auth.user` is `User(id, username, Role.EDITOR)`. This single place caps `require_admin`, `effective_access` and `job_out`.
- Produces: `token_out` adds `scope` and `expires_at`.

`NOTEBOOK_SCOPE_ROUTES` covers every current `/api/v1` route (55 operations: 4 public, 36 allowed, 15 denied) **except** the ones below. The SDK uses `DELETE .../datasets/{id}` for its temporary predict input, which is why deletes stay allowed.

| Not allowed for notebook tokens | Why |
|---|---|
| `/api/v1/auth/me`, `/auth/logout`, `/auth/password` | password change, sessions; the relay refuses every `/auth/*` too |
| `/api/v1/tokens`, `/api/v1/tokens/{token_id}` (all methods) | no new or longer-lived credentials |
| `/api/v1/users`, `/api/v1/users/{user_id}` (all methods) | account administration |
| `POST /api/v1/modules`, `DELETE /api/v1/modules/{module_id}` | code that runs unsandboxed on the Fione host |
| `POST /api/v1/projects/{project_id}/models/import` | untrusted pickles load on the Fione host |
| `POST /api/v1/projects/{project_id}/share`, `DELETE /api/v1/projects/{project_id}/share/{username}` | sharing changes permissions that outlive the 12 h token; the SDK does not use them (ruling) |

- [ ] **Step 1: Write the failing tests** in `tests/api/test_token_scope.py`. It is a separate file; the existing matrix keeps its arity. `api_helpers.bearer` makes full tokens, so seed notebook tokens with `service.create_token`. Seed tokens with `create_token(..., scope=TokenScope.NOTEBOOK, expires_at=expiry_after(3600))`.
  - `test_every_api_route_is_classified_for_notebook_tokens`: the set of `(method, path)` from `app.openapi()["paths"]` (as `tests/api/test_permissions.py::test_matrix_covers_every_route` does; `app.routes` is not flat) equals `ALLOWED | DENIED | PUBLIC`, three disjoint tables in the test file. `PUBLIC` holds the routes that never call `get_auth`, where a bearer header is ignored: `POST /auth/login`, `POST /auth/first-admin`, `GET /auth/status`, `GET /health`. Check the real list.
  - `test_public_routes_grant_a_notebook_token_nothing`: on each `PUBLIC` route, the response with a notebook token equals the anonymous one (status and body), and no cookie is set on `/auth/login` for wrong credentials.
  - `test_notebook_token_is_refused_on_denied_routes`: parametrized over `DENIED` → 403 with `code == "token_scope"`, and nothing changes (token count, user count, modules).
  - `test_notebook_token_works_on_allowed_routes`: a sample `GET /projects`, `POST /projects`, dataset upload, `POST .../jobs/automl` → not 403.
  - `test_admin_notebook_token_has_editor_power`: an admin's notebook token on `GET /api/v1/projects` lists only the admin's own and shared projects, `POST .../models/import` → 403, and another user's project → 404.
  - `test_expired_token_is_401`: `expires_at` 1 s in the past → 401. 60 s ahead → 200.
  - `test_bearer_created_token_inherits_scope_and_expiry`: a full token with `expires_at=E` creates a token through `POST /tokens` → the new token has `scope == "full"` and `expires_at == E`. A full token without expiry creates one without expiry.
  - `test_cookie_session_is_unaffected`: a cookie `POST /tokens` with CSRF → 201, `scope == "full"`, `expires_at is None`.
- [ ] **Step 2:** Run `uv run pytest tests/api/test_token_scope.py -q`. Expected: FAIL (`ImportError: TokenScope`).
- [ ] **Step 3:** Implement the interfaces above. `create_token` in `routes_users.create_token` passes `scope=auth.scope` and `expires_at=auth.token.expires_at` when `auth.via == "bearer"`.
- [ ] **Step 4:** Add unit tests to `tests/unit/test_auth.py`:
  - `test_migration_keeps_existing_tokens_full_and_unexpiring`: a DB migrated to the previous version with one token, migrated again → `scope == "full"`, `expires_at is None`.
  - `test_create_token_rejects_iso_t_format`: `expires_at="2026-01-01T00:00:00"` → `ValueError`.
- [ ] **Step 5:** Account page: the tokens table shows an "expired" state next to revoked/active, a scope badge (`account.token_scope_notebook`) and the expiry (`account.token_expires`) through the existing `utc` filter. Add the keys to both `en.json` and `ja.json`. In `docs/known-limitations.md`, replace "API tokens never expire" with: tokens you create never expire, and notebook tokens expire with their container. Update the Japanese summary line too. Update the account screenshot in `scripts/ui-screenshots.py`.
- [ ] **Step 6:** Run `uv run pytest tests/api tests/unit/test_auth.py tests/unit/test_i18n.py tests/unit/test_docs.py tests/web/test_account_ui.py -q`. Expected: all pass. Then `uv run ruff check . && uv run ruff format --check .` must be clean.
- [ ] **Step 7:** Commit "Add API token scope and expiry; cap notebook tokens".

### Task 2: fione-sdk core (client, projects, datasets)

**Files:**
- Create: `sdk/pyproject.toml`, `sdk/README.md`, `sdk/src/fione_sdk/{__init__,client,errors}.py`
- Test: `tests/sdk/{conftest,test_client,test_datasets,test_version}.py`
- Modify: `pyproject.toml` (pytest `pythonpath` adds `"sdk/src"`), `tests/unit/test_docs.py` (known names also from `sdk/src/fione_sdk/*.py`), `docs/configuration.md` (new section "fione-sdk": `FIONE_URL`, `FIONE_TOKEN`)

**Interfaces:**
- Consumes: the `/api/v1` routes (Task 1 tokens via `Authorization: Bearer`). Error bodies are `{"error": "<message>", "code": "<slug>"}`.
- Produces:
  - `fione_sdk.__version__ = "20.0.0"`.
  - `sdk/pyproject.toml`: hatchling, `name = "fione-sdk"`, static `version = "20.0.0"`, `requires-python = ">=3.12"`, `dependencies = ["httpx>=0.28.1", "pandas>=2.2"]`, `license = { text = "Apache-2.0" }`.
- Produces: `FioneError(Exception)` with `status: int`, `code: str` and `message: str`.
- Produces: `Client(url: str | None = None, token: str | None = None, *, http: httpx.Client | None = None, timeout: float = 60.0)`.
  - `url`/`token` default to the env vars `FIONE_URL` and `FIONE_TOKEN`. A missing token raises `FioneError(0, "config", "set FIONE_TOKEN or pass token=")`. A missing URL raises the same when `http` is None.
  - Every request sends `Authorization: Bearer <token>`. A non-2xx response raises `FioneError` from the body (`code="http"` when the body is not JSON).
- Produces, all returning the API's JSON as `dict`/`list[dict]` unless noted:
  - `projects()`, `project(project_id: str)`, `create_project(name: str)`
  - `datasets(project_id)`, `dataset(project_id, dataset_id: int)`
  - `upload(project_id, df: pd.DataFrame, name: str, type: Literal["train","test","predict"] = "train") -> dict`: multipart `name`, `type`, `file` (`f"{name}.csv"`, CSV from `df.to_csv(index=False)`)
  - `read(project_id, dataset_id) -> pd.DataFrame`: streams the `download` route into `pd.read_csv`
  - `preview(project_id, dataset_id, **params) -> dict`, `profile(project_id, dataset_id) -> dict`
  - `column_profile(project_id, dataset_id, column: str) -> dict`: the column is URL-quoted with `safe=""`
  - `delete_dataset(project_id, dataset_id) -> None`

- [ ] **Step 1: Write the failing tests.** `tests/sdk/conftest.py` provides `sdk(make_client)`: a `Client(token=<editor bearer>, http=<TestClient>)`, using `api_helpers.add_user`/`bearer`.
  - `test_upload_then_read_round_trips_a_frame`: a 3-column frame with a Japanese column name and a NaN → `read` equals it (`pd.testing.assert_frame_equal(check_dtype=False)`).
  - `test_errors_carry_status_and_code`: `project("missing")` → `FioneError` with `status == 404`. With a viewer's token, `upload` → 403.
  - `test_env_configures_the_client`: `monkeypatch.setenv("FIONE_TOKEN", t)` plus `http=` → works. No token → `FioneError` with `code == "config"`.
  - `test_notebook_token_works_with_the_sdk`: a `TokenScope.NOTEBOOK` token can list, upload and read.
  - `test_column_name_with_slash_is_quoted`: `column_profile(..., "a/b")` → 200.
  - `test_sdk_version_matches_fione`: `fione_sdk.__version__ == fione.version.__version__`, and `sdk/pyproject.toml`'s `version` (read with `tomllib`) is equal.
- [ ] **Step 2:** Run `uv run pytest tests/sdk -q`. Expected: FAIL (`ModuleNotFoundError: fione_sdk`).
- [ ] **Step 3:** Implement. `sdk/README.md` covers installing (`pip install ./sdk`), `FIONE_URL`/`FIONE_TOKEN`, and an example. Add the "fione-sdk" section to `configuration.md` and extend `test_docs.py`'s known names with `sdk/src/fione_sdk/*.py`.
- [ ] **Step 4:** Run `uv run pytest tests/sdk tests/unit/test_docs.py -q`. Expected: pass. Also `uv build sdk` builds a wheel `fione_sdk-20.0.0-py3-none-any.whl`, which you then delete. Ruff clean.
- [ ] **Step 5:** Commit "Add fione-sdk: client, projects and datasets".

### Task 3: fione-sdk jobs, leaderboard, predict, modules

**Files:**
- Create: `sdk/src/fione_sdk/jobs.py`
- Modify: `sdk/src/fione_sdk/{__init__,client,errors}.py`, `sdk/README.md`
- Test: `tests/sdk/test_sdk_jobs.py`

**Interfaces:**
- Consumes: Task 2 `Client`. Routes: `POST /projects/{pid}/jobs/automl` (`{"dataset_id", "config", "name"}`), `jobs/batch-predict` (`{"model_id", "dataset_id", "include_columns", "name"}`) and `jobs/module` (`{"module_id", "dataset_id", "params", "name"}`); `GET /jobs/{id}`; `GET /jobs/{id}/events?after=&limit=` (returns `events`, `last_id`, `status`); `POST /jobs/{id}/cancel`; `GET /projects/{pid}/models`; `GET /models/{id}`; `GET /modules`. Terminal statuses: `done|failed|cancelled`. Results: training `{"model_id", ...}`; batch-predict and module `{"dataset_id", ...}` (module jobs may add `module_model_id`).
- Produces: `JobFailed(FioneError)` with `job: Job`; `code` is `"failed"` or `"cancelled"`, and `message` is the job's message.
- Produces: `Job` with `id: int`, `data: dict` (last fetched), properties `status: str` and `result: dict | None`, and these methods:
  - `refresh() -> Job`
  - `wait(timeout: float | None = None, poll: float = 1.0, max_poll: float = 10.0) -> Job`: the poll interval doubles up to `max_poll`. It raises `JobFailed` on failed/cancelled and `TimeoutError` past `timeout`. On `KeyboardInterrupt` it cancels the job and re-raises.
  - `events(after: int = 0, *, follow: bool = False) -> Iterator[dict]`: pages by `last_id`. With `follow`, it keeps polling until the status is terminal and a page is empty.
  - `cancel() -> Job`
- Produces on `Client`:
  - `train(project_id, dataset_id: int, target: str, *, name: str | None = None, **config) -> Job`: `config = {"target": target, **config}`
  - `job(job_id: int) -> Job`
  - `models(project_id) -> pd.DataFrame`: one row per model
  - `model(model_id) -> dict`
  - `leaderboard(model_id) -> pd.DataFrame`: from `model(...)["leaderboard"]`
  - `predict(project_id, model_id: int, df, *, include_columns: list[str] | None = None, timeout: float | None = None) -> pd.DataFrame`: uploads `df` as a `predict` dataset named `sdk_predict_<8 hex>`, submits batch-predict, waits, reads `result["dataset_id"]`, and deletes the uploaded input in a `finally`. The result dataset stays in Fione.
  - `modules() -> list[dict]`
  - `run_module(project_id, module_id: str, dataset_id: int, params: dict | None = None, *, name: str | None = None) -> Job`

- [ ] **Step 1: Write the failing tests** (`make_client(start_runner=True)`, iris from `api_helpers.iris_frame()`, `max_runtime_secs=10`).
  - `test_train_wait_and_leaderboard`: `train(...).wait(timeout=120)` → `status == "done"`. `leaderboard(job.result["model_id"])` has the columns `model` and `cv_score`. `models(pid)` has 1 row.
  - `test_events_follow_ends_at_a_terminal_status`: `list(job.events(follow=True))` is non-empty, its last event has type `finished` or `stopped`, and it ends without hanging (`timeout` guard).
  - `test_predict_returns_rows_in_order_and_removes_its_input`: 5 rows → 5 rows with a `predict` column, in input order. Afterwards `datasets(pid)` has no `sdk_predict_*` entry.
  - `test_cancel_raises_job_failed_cancelled`: train with `max_runtime_secs=60`, `cancel()`, then `wait()` → `JobFailed` with `code == "cancelled"`.
  - `test_failed_job_raises_with_message`: `train(..., target="missing")` → `FioneError` 422 at submission. A module job that fails at run time (built-in `sort` with a column that is not in the data; the submission only validates the parameter schema) → `JobFailed` with `code == "failed"`.
  - `test_run_module_returns_a_dataset`: built-in `sort` on iris → `read(pid, job.result["dataset_id"])` is sorted.
  - `test_wait_timeout`: `wait(timeout=0.01)` on a queued job (runner off) → `TimeoutError`.
- [ ] **Step 2:** Run `uv run pytest tests/sdk/test_sdk_jobs.py -q`. Expected: FAIL (`AttributeError: train`).
- [ ] **Step 3:** Implement. In the README, document train, wait, events, predict and run_module, and that modules run on the server.
- [ ] **Step 4:** Run `uv run pytest tests/sdk -q`. Expected: pass. Ruff clean.
- [ ] **Step 5:** Commit "fione-sdk: jobs, leaderboard, predict and modules".

### Task 4: Per-user notebook permission

**Files:**
- Modify: `src/fione/db.py` (append a migration), `src/fione/auth/{roles,service}.py`, `src/fione/api/{routes_users,schemas}.py`, `src/fione/web/admin_ui.py`, `src/fione/web/templates/admin_users.html`, `src/fione/i18n/{en,ja}.json`, `scripts/ui-screenshots.py`
- Test: `tests/unit/test_auth.py`, `tests/api/test_projects_users_api.py` (the exact-shape assertion for `POST /users` gains `notebook`), `tests/web/test_admin_ui.py`, `tests/web/test_routes.py` (`ADMIN_ROUTES` gains `("POST", "/admin/users/{uid}/notebook")` and the form table its fields)

**Interfaces:**
- Consumes: `auth.service` (`UserNotFound`, `get_user`, `set_role`), `routes_users` and the `UserPatch` schema, `web/access.py` (`form_auth`, `admin_only`), and Task 1's `TokenScope` (for the scope test).
- Produces:
  - Migration: `ALTER TABLE users ADD COLUMN notebook TEXT NOT NULL DEFAULT 'none' CHECK (notebook IN ('none','run'))`.
  - `NotebookPermission(StrEnum)`: `NONE = "none"`, `RUN = "run"` in `fione.auth.roles`. `User` is **not** changed, because it is constructed all over the code.
- Produces:
  - `service.get_notebook_permission(conn, user_id: int) -> NotebookPermission` (`UserNotFound`)
  - `service.set_notebook_permission(conn, user_id: int, perm: NotebookPermission) -> None` (`UserNotFound`)
  - `service.notebook_permissions(conn) -> dict[int, NotebookPermission]`
  - `service.can_use_notebook(conn, user: User) -> bool`: True for admins; otherwise the stored value is `RUN`. It is read fresh every time.
- Produces:
  - `UserPatch.notebook: Literal["none","run"] | None`. An empty patch (no role, password or notebook) is still a 422; `update_user`'s guard must consider `notebook`.
  - `user_out(user, *, notebook: NotebookPermission | None = None)` adds `"notebook"` when given. `GET /users`, `POST /users` and `PATCH /users/{id}` always give it.
  - UI: `POST /admin/users/{uid}/notebook` (form `notebook`, `csrf_token`; `form_auth`; admin only).

- [ ] **Step 1: Write the failing tests.**
  - `test_notebook_permission_defaults_to_none_for_editors_and_viewers`.
  - `test_admins_can_always_use_notebooks`: an admin with stored `none` → `can_use_notebook` is True.
  - `test_patch_sets_notebook_permission`: admin `PATCH {"notebook": "run"}` → 200 with `"notebook": "run"`. An editor → 403. A notebook token (Task 1) → 403 `token_scope`.
  - `test_admin_ui_toggles_permission`: posting with a CSRF token → 303 and stored. Without CSRF → 403. A foreign `Origin` → 403. An editor posting → 403.
  - `test_users_page_shows_the_notebook_column`: every user row shows `users.notebook_run` or `users.notebook_none`. Admin rows show `users.notebook_admin` and no control.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_auth.py tests/api/test_projects_users_api.py tests/web/test_admin_ui.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. Add the i18n keys `users.notebook_*` in both languages, and the users-page screenshot.
- [ ] **Step 4:** Run the same files plus `tests/unit/test_i18n.py tests/api/test_permissions.py -q`. Expected: pass. Ruff clean.
- [ ] **Step 5:** Commit "Add the per-user notebook permission".

### Task 5: `fione_notebook` Jupyter Server extension

**Files:**
- Create: `src/fione_notebook/{__init__,auth,config}.py`
- Test: `tests/notebook/{conftest,test_launch_token,test_jupyter_server}.py` (`conftest.py` skips the directory with `collect_ignore_glob` when `jupyter_server` is not installed, since `-m` deselection happens after collection)
- Modify: `pyproject.toml`: the dependency group `notebook` is `jupyter_server==2.21.1`, `jupyterlab==4.6.4`, `ipykernel==7.4.0`, `tornado>=6.5,<6.6`, `pandas`, `pyarrow`, `httpx>=0.28.1`, `scikit-learn`, `matplotlib`. Plotting and scikit-learn are in because without egress the image is the whole library set. Also add the `notebook` and `docker` markers and extend `addopts` with `and not docker and not notebook`.
- Modify: `uv.lock` (`uv lock`), `.github/workflows/ci.yml` (`uv sync --frozen --group notebook` replaces `uv sync --frozen` in the `test` job, and a step `uv run pytest -m notebook -q` follows the default test step)

**Interfaces:**
- Consumes: jupyter_server 2.21.1's `IdentityProvider`, `Authorizer`, `JupyterHandler` and `allow_unauthenticated`. Nothing from `fione`: the package runs only inside the notebook image.
- Produces in `fione_notebook.auth`:
  - `LAUNCH_PARAM = "launch"`.
  - `verify_launch_token(key: bytes, token: str, *, owner: str, now: float | None = None) -> dict | None`. The format is `v1.<b64url(json)>.<b64url(HMAC-SHA256(key, "v1." + payload))>`, with claims `sub: str` (the Fione user id), `name: str`, `role: "admin"|"editor"|"viewer"`, `exp: int`, `jti: str` (≥ 16 chars). It returns None on a wrong version, bad base64/JSON, an HMAC mismatch, an expired token, `sub != owner` or a missing `jti`.
- Produces in `fione_notebook.auth`:
  - `FioneLoginHandler`: `@allow_unauthenticated GET <base_url>login?launch=&next=` → 403 unless the token verifies and its `jti` is unused. An in-process dict of used `jti` values pruned by `exp` is enough, since a container is one process. On success it calls `set_login_cookie` and redirects to `next` only when it is a path under `base_url`, otherwise to `<base_url>lab`.
  - `FioneIdentityProvider`: `token=""`, `get_user_token` returns None, the cookie carries `{username, name, role}`, and `user_from_cookie` refuses a non-owner. `validate_security` exits when the owner or the 32-byte key is missing.
  - `FioneAuthorizer`: deny unless `user.username == owner`; then allow only the pairs in the table below.
- Produces in `fione_notebook.config`: `configure(c, env: Mapping[str, str]) -> None`. It reads `FIONE_NB_OWNER` (digits), `FIONE_NB_KEY` (64 hex), `FIONE_NB_COOKIE_SECRET` (64 hex), `FIONE_NB_ORIGIN` (Fione's public origin) and `FIONE_NB_EXPIRES` (epoch seconds), and sets:
  - `ServerApp.identity_provider_class`, `authorizer_class`; `ip="0.0.0.0"`, `port=8888`, `base_url=f"/user/{owner}/"`, `root_dir="/home/nb/work"`.
  - `allow_unauthenticated_access=False`, `allow_remote_access=True`, `open_browser=False`, `cookie_secret`.
  - `extra_log_scrub_param_keys=["launch"]`.
  - `tornado_settings.headers["Content-Security-Policy"] = f"frame-ancestors 'self' {origin}; report-uri /user/{owner}/api/security/csp-report"`.
  - `IdentityProvider.cookie_options={"samesite": "Lax", "expires_days": d}` and `get_secure_cookie_kwargs={"max_age_days": d}`, with `d = max(expires - now, 0) / 86400`.
  - `MappingKernelManager.cull_idle_timeout=1800`, `cull_interval=300`; `ServerApp.shutdown_no_activity_timeout=3600`; `terminals_enabled=True` (gated by the Authorizer).
  - It rejects malformed values with `SystemExit`.
  - It also exits when `JUPYTER_CONFIG_DIR` or `JUPYTER_DATA_DIR` is unset, or is writable by the running uid (`os.access(..., os.W_OK)`), or when `JUPYTER_PATH` is set. This is the shared-origin rule of the Global Constraints. Tests pass root-owned-equivalent directories made read-only with `chmod 0555`.

| Granted to the owner | (resource, action) |
|---|---|
| everyone signed in (role editor or viewer) | `contents`, `kernelspecs`, `sessions`, `kernels`, `config`, `api`, `events`: read; `contents`, `sessions`, `kernels`, `config`, `events`: write; `kernels`, `events`, `lsp`: execute; `lsp`, `nbconvert`: read |
| role `admin` in addition | `terminals`: read, write, execute; `server`: write |

A viewer who was granted notebooks runs code too: their boundary is their read-only Fione token, not Jupyter.

- [ ] **Step 1: Write the failing unit tests** in `tests/notebook/test_launch_token.py`. They use a local `sign()` helper written in the test from the format above.
  - `test_accepts_a_fresh_token_for_the_owner`.
  - `test_rejects`, parametrized: expired by 1 s, one flipped signature byte, `sub` of another user, no `jti`, `v2.` prefix, three dots, non-JSON payload → None.
  - `test_configure_sets_the_security_traits`: on a `traitlets.config.Config`, check `allow_unauthenticated_access is False`, the CSP string exactly, `extra_log_scrub_param_keys == ["launch"]`, the culling values, and `base_url == "/user/7/"`.
  - `test_configure_refuses_malformed_env`: a non-digit owner, a 63-hex key, an origin with a path → `SystemExit`.
- [ ] **Step 2: Write the failing server tests** in `tests/notebook/test_jupyter_server.py`. A module-scoped fixture runs `python -m jupyterlab` (`jupyter lab --no-browser`) on a free 127.0.0.1 port, with a temp `HOME`, a writable temp `JUPYTER_RUNTIME_DIR`, and temp `JUPYTER_CONFIG_DIR`/`JUPYTER_DATA_DIR` made mode 0555 after the config file is written, with owner 7, random key and cookie secret, and `FIONE_NB_ORIGIN=http://127.0.0.1:18080`. A config file in the temp config dir calls `configure(c, os.environ)`, and `root_dir` is overridden to a temp dir after `configure`. The server's stderr is captured to a file. Kernel and terminal WebSockets use `tornado.websocket.websocket_connect`.
  - `test_anonymous_lab_redirects_to_login`: 302 to a `Location` starting `/user/7/login`.
  - `test_anonymous_api_and_status_are_403`.
  - `test_login_refuses_bad_tokens`: missing, expired, tampered, reused, other-owner → 403 each.
  - `test_login_sets_an_httponly_lax_cookie_on_the_base_url`: `Set-Cookie` contains `HttpOnly`, `SameSite=Lax` and `Path=/user/7/`, the token is not in the response body, and the response is 302 to `/user/7/lab`.
  - `test_next_outside_the_base_url_goes_to_lab`: `next=https://evil.example/` or `next=/other/` → `Location: /user/7/lab`.
  - `test_token_param_and_header_are_ignored`: `?token=x` and `Authorization: token x` → still 403 (never token-authenticated).
  - `test_cookie_post_needs_xsrf`: `POST /user/7/api/contents` with the cookie and no `X-XSRFToken` → 403; with the `_xsrf` cookie echoed → 201.
  - `test_kernel_runs_code`: start a kernel, run `print(6*7)` over the channels WebSocket → the stream text is `42\n`.
  - `test_foreign_origin_websocket_is_refused`: `Origin: http://evil.example` → 403.
  - `test_editor_cannot_use_terminals_or_shutdown`: `POST /api/terminals`, `POST /api/shutdown` → 403. The terminal WebSocket is 403 for anonymous and editor.
  - `test_admin_can_open_a_terminal`: an admin-role launch → `POST /api/terminals` 200, and `echo ok` over its WebSocket prints `ok`.
  - `test_csp_header`: every response's CSP equals the configured string.
  - `test_launch_token_never_reaches_the_log`: after all logins, no token used in this module appears in the captured log.
  - `test_server_refuses_to_start_without_owner_or_key`: exit code ≠ 0 within 20 s. The same holds with a writable `JUPYTER_DATA_DIR` and with `JUPYTER_PATH` set.
  - `test_user_written_html_is_never_served`: as the owner, write `x.html` (with a `<script>`) to `~/.local/share/jupyter/labextensions/evil/static/`, to `~/.jupyter/`, and to the contents root. Then:
    - `/user/7/lab/extensions/evil/static/x.html`, fetched anonymously and as the owner → 404;
    - `/user/7/files/x.html` → 200 with a CSP containing `sandbox allow-scripts`;
    - `/user/7/nbconvert/html/<a notebook>` → a CSP containing `sandbox allow-scripts`.
- [ ] **Step 3:** Run `uv sync --group notebook && uv run pytest -m notebook tests/notebook -q`. Expected: FAIL (`ModuleNotFoundError: fione_notebook`).
- [ ] **Step 4:** Implement `src/fione_notebook`.
- [ ] **Step 5:** Run `uv run pytest -m notebook tests/notebook -q` → all pass. Run `uv run pytest -q` → unchanged and passing (notebook tests deselected). Ruff clean.
- [ ] **Step 6:** Commit "Add fione_notebook: launch-token sign-in and owner-only authorization for Jupyter".

### Task 6: Notebook image, licences and release

**Files:**
- Create: `docker/Dockerfile.notebook`, `docker/Dockerfile.notebook.dockerignore`, `docker/notebook/jupyter_server_config.py` (one call: `configure(c, os.environ)`), `docker/notebook/page_config.json` (`{"disabledExtensions": {"@jupyterlab/apputils-extension:announcements": true}}`)
- Modify: `scripts/check_licenses.py`, `tests/unit/test_check_licenses.py`, `.github/workflows/release.yml`
- Test: `tests/docker/test_notebook_image.py` (`docker` marker)

**Interfaces:**
- Consumes: the Task 5 group `notebook`, `fione_notebook`, and `sdk/`.
- Produces:
  - The image `ghcr.io/codelibs/fione-notebook:<tag>`.
  - Build stage: `python:3.12.15-slim-trixie` with uv, `uv sync --frozen --no-install-project --only-group notebook`, then `uv pip install --no-deps ./sdk`.
  - Runtime: user `nb` with uid/gid 1000, `HOME=/home/nb`, `WORKDIR /home/nb/work`, `src/fione_notebook` on `PYTHONPATH`.
  - `JUPYTER_CONFIG_DIR=/etc/jupyter-fione` and `JUPYTER_DATA_DIR=/usr/local/share/jupyter-fione`, both root-owned and mode 0555; `JUPYTER_RUNTIME_DIR=/tmp/jupyter-runtime` (writable, not served). The venv is root-owned and not writable by `nb`. The settings and workspaces writes then fail in the server too, which matches the gateway rule. The config goes to `/etc/jupyter/jupyter_server_config.py`, and `page_config.json` to `<venv>/etc/jupyter/labconfig/`.
  - `EXPOSE 8888`, `CMD ["jupyter", "lab", "--no-browser"]`.
  - `HEALTHCHECK`: Python `urlopen` of `http://127.0.0.1:8888/user/${FIONE_NB_OWNER}/login`. Any HTTP status, 403 included, counts as up; a connection error counts as down.
  - No package install at start.
- Produces in `check_licenses`:
  - `EXCEPTIONS` gains `certifi` ("MPL-2.0 CA bundle, unmodified, via httpx") and `fqdn` ("MPL-2.0, unmodified, via jupyter_events"); this only turns their `review` label into a recorded exception.
  - `BUNDLE_REVIEWED: dict[str, str]` holds `elkjs` and `@fortawesome/fontawesome-free` with their licences and the reason "bundled by JupyterLab in the opt-in notebook image, not vendored; confirmed by the maintainer".
  - `bundle_licenses(path: Path) -> list[tuple[str, str, Verdict]]` reads JupyterLab's `static/third-party-licenses.json`; check the file's real keys before writing the parser.
  - `main()` also checks the bundle when the `jupyterlab` distribution is installed (the existing `main()` tests stub it, so they do not depend on the environment). A bundled package that is neither `allowed` nor in `BUNDLE_REVIEWED` fails.

- [ ] **Step 1: Write the failing tests.**
  - `test_certifi_and_fqdn_are_exceptions`.
  - `test_bundle_unknown_epl_package_fails`: a temp JSON file with an `EPL-2.0` package not in `BUNDLE_REVIEWED` → `main`'s bundle check returns failure.
  - `test_bundle_reviewed_packages_pass`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_check_licenses.py -q` → FAIL. Implement. Then `uv run python scripts/check_licenses.py` (with the notebook group installed) must exit 0, and the bundle lines show `elkjs` and FontAwesome as reviewed exceptions.
- [ ] **Step 3: Write the docker tests**, which build the image once per module with `docker build -f docker/Dockerfile.notebook -t fione-notebook:test .`.
  - `test_runs_as_uid_1000`.
  - `test_pinned_versions`: `jupyter --version` shows `jupyter_server: 2.21.1`, `jupyterlab: 4.6.4`, and tornado 6.5.x.
  - `test_licence_check_passes_in_the_image`: `python scripts/check_licenses.py`, mounted read-only → exit 0.
  - `test_sdk_importable`: `python -c "import fione_sdk; print(fione_sdk.__version__)"` → `20.0.0`.
  - `test_announcements_disabled`: `jupyter labextension list` shows the plugin disabled.
  - `test_jupyter_dirs_are_not_writable_by_nb`: as uid 1000, `touch` in `$JUPYTER_CONFIG_DIR`, `$JUPYTER_DATA_DIR` and the venv's `share/jupyter` fails.
- [ ] **Step 4:** Run `uv run pytest -m docker tests/docker/test_notebook_image.py -q`. Expected: pass. Record the image size for the docs (Task 11).
- [ ] **Step 5:** In `release.yml`, add two `docker/build-push-action` steps with the same SHA pin: `fione-notebook` from `docker/Dockerfile.notebook`, and `fione-notebook-launcher` from `docker/Dockerfile.launcher` (Task 7; add that step in Task 7 if this task lands first). Both use the tag build-arg.
- [ ] **Step 6:** Commit "Add the notebook image and its licence checks". **The PR description must ask the maintainer to confirm** elkjs (EPL-2.0) and FontAwesome (CC-BY-4.0 AND OFL-1.1 AND MIT). They are bundled by JupyterLab in the opt-in image, built from PyPI and not vendored.

### Task 7: notebook-launcher service

**Files:**
- Create: `src/fione_launcher/{__init__,__main__,config,docker,spec,server}.py`, `docker/Dockerfile.launcher`
- Test: `tests/launcher/{test_spec,test_launcher_server,test_reconcile}.py`, `tests/docker/test_launcher_docker.py` (`docker`)
- Modify: `docs/configuration.md` (new section "Notebook launcher"), `tests/unit/test_docs.py` (that section's table equals the `"FIONE_*"` names in `src/fione_launcher/*.py`, which also become known names)

**Interfaces:**
- Produces `config.LauncherConfig.from_env(env) -> LauncherConfig`:
  - `FIONE_LAUNCHER_SECRET` (required, ≥ 32 chars, otherwise exit 1).
  - `FIONE_NOTEBOOK_IMAGE` (required).
  - `FIONE_NOTEBOOK_API_URL` (default `http://notebook-gateway:8081`).
  - `FIONE_NOTEBOOK_MAX_RUNNING` (default 4: each container may take 4 GiB).
  - The socket is fixed at `/var/run/docker.sock`; port 8000.
- Produces `docker.DockerAPI(socket_path: str)` (stdlib `http.client` over `AF_UNIX`):
  - `request(method: str, path: str, body: dict | None = None) -> tuple[int, Any]`.
  - Helpers `inspect_self()`, `find_network(project: str, name: str) -> str`, `list_notebooks(project) -> list[dict]`, `create_volume(name, labels)`, `create(name, body)`, `start(id)`, `remove(id)`.
  - The image is never pulled.
- Produces `spec.container_body(cfg, *, project: str, network: str, uid: str, req: StartRequest) -> dict`, the exact create body:
  - `Image` = `cfg.image`; `User` = `"1000:1000"`.
  - `Env` = `FIONE_NB_OWNER`, `FIONE_NB_KEY`, `FIONE_NB_COOKIE_SECRET`, `FIONE_NB_ORIGIN`, `FIONE_NB_EXPIRES`, `FIONE_URL` = `cfg.api_url`, `FIONE_TOKEN`.
  - `Labels` = `fione.notebook=1`, `fione.project`, `fione.uid`, `fione.expires`.
  - `HostConfig` holds exactly these keys: `NanoCpus=2_000_000_000`, `Memory=MemorySwap=4294967296`, `PidsLimit=512`, `CapDrop=["ALL"]`, `SecurityOpt=["no-new-privileges:true"]`, `AutoRemove=True`, `Init=True`, `NetworkMode=network`, `Mounts=[{"Type": "volume", "Source": f"{project}-nb-home-{uid}", "Target": "/home/nb/work"}]`.
  - `NetworkingConfig.EndpointsConfig[network].Aliases = [f"nb-{uid}"]`. That alias is what nginx resolves, scoped to the network.
  - The container name is `f"{project}-nb-{uid}"`.
- Produces: `StartRequest` is validated before any Docker call, else 422:
  - `uid`: `^[1-9][0-9]{0,17}$`.
  - `launch_key` and `cookie_secret`: `^[0-9a-f]{64}$`.
  - `token`: `^fione_[A-Za-z0-9_-]{20,100}$`.
  - `fione_origin`: `^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$`.
  - `expires_at`: an int in (now, now + 7 days].
  - No other field is accepted.
- Produces the HTTP API. Every route except `/health` requires `X-Fione-Launcher-Secret`, compared with `hmac.compare_digest`; a wrong or missing one gets 401. JSON errors are `{"error": code}`.

| Route | Result |
|---|---|
| `GET /health` | 200 `{}` |
| `PUT /notebooks/{uid}` + `StartRequest` body | 200 `{"state": "starting"\|"running"}`; 409 `exists` (a container is there); 409 `limit` (`max_running` reached); 503 `image_missing`; 422 `invalid` |
| `GET /notebooks/{uid}` | 200 `{"state": "absent"\|"starting"\|"running"}`: `running` once Docker health is `healthy` |
| `DELETE /notebooks/{uid}` | 204, idempotent; the volume is kept |

- Produces lifecycle behaviour:
  - At start, `inspect_self()` (by hostname) gives the label `com.docker.compose.project`. The network is the one labelled `com.docker.compose.project=<p>` and `com.docker.compose.network=notebooks`. If either is missing, exit 1.
  - At start and on SIGTERM, every container labelled `fione.notebook=1,fione.project=<p>` is removed. A reaper thread removes containers whose `fione.expires` has passed, every 60 s.
  - Nothing logs the request body, the token or the keys.
- Produces `docker/Dockerfile.launcher`: `python:3.12.15-slim-trixie`, copy `src/fione_launcher`, `CMD ["python", "-m", "fione_launcher"]`. It runs as root so it can open a root-owned socket portably; Compose drops all capabilities and makes the filesystem read-only (Task 9). It has a `HEALTHCHECK` on `/health`.

- [ ] **Step 1: Write the failing unit tests** with a `FakeDocker` that records calls and has the same methods as `DockerAPI`. The server runs on a free port in a thread.
  - `test_container_body_is_exactly_the_fixed_spec`: equality with a literal expected dict. `set(body["HostConfig"]) == {expected keys}`, and none of `Binds`, `Privileged`, `PortBindings`, `CapAdd`, `Devices`, `PublishAllPorts` is present.
  - `test_invalid_requests_never_reach_docker`, parametrized: uid `0`, `1a`, `../1`, 19 digits; key with 63 hex or uppercase; token containing `\n`; origin with a path; `expires_at` in the past or 8 days ahead; an extra field `image` → 422 and `FakeDocker.calls == []`.
  - `test_secret_required`: no or wrong header → 401 on PUT, GET and DELETE. `/health` → 200 without it.
  - `test_put_twice_is_409_exists`, `test_limit_is_409`, `test_missing_image_is_503`.
  - `test_state_follows_health`: Docker health `starting` → `starting`, `healthy` → `running`, no container → `absent`.
  - `test_reconcile_removes_only_this_projects_notebooks`: fake containers of projects `a` and `b` → only `a`'s are removed.
  - `test_reaper_removes_expired`.
  - `test_logs_hold_no_secrets`: with `caplog`, a full PUT logs nothing containing the token, the key or the cookie secret.
- [ ] **Step 2:** Run `uv run pytest tests/launcher -q`. Expected: FAIL (`ModuleNotFoundError`). Implement. Run again → pass.
- [ ] **Step 3: Write the docker integration test** (`-m docker`). It runs a launcher container built from `Dockerfile.launcher` in a throwaway compose project with an internal `notebooks` network, and mounts the socket. `FIONE_NOTEBOOK_IMAGE` is a test image built inline (`FROM python:3.12.15-slim-trixie`, `CMD ["sleep","300"]`, a `HEALTHCHECK` that always passes).
  - `test_started_container_has_the_spec`: `docker inspect` shows NanoCpus, Memory, PidsLimit, CapDrop ALL, no-new-privileges, AutoRemove, the labels, the alias `nb-<uid>` and a single network. `docker volume inspect` shows the per-user volume.
  - `test_no_egress`: `docker exec` of a Python `socket.create_connection` to `pypi.org:443` and `1.1.1.1:443` fails, and `host.docker.internal` does not resolve.
  - `test_stop_removes_container_and_keeps_volume`.
  - `test_sigterm_removes_all`.
  - Teardown removes the containers, volumes and networks labelled with the project.
- [ ] **Step 4:** Run `uv run pytest -m docker tests/docker/test_launcher_docker.py -q` → pass. Add the "Notebook launcher" section to `configuration.md`. Run `uv run pytest tests/launcher tests/unit/test_docs.py -q` → pass. Ruff clean.
- [ ] **Step 5:** Commit "Add the notebook launcher: fixed-spec per-user containers over the Docker socket".

### Task 8: Fione launch flow (notebook page)

**Files:**
- Create: `src/fione/notebooks/{__init__,launch,launcher,service}.py`, `src/fione/web/notebook_ui.py`, `src/fione/web/templates/{notebook,_notebook_status}.html`, `src/fione/web/static/css/` (frame styles in the existing stylesheet)
- Modify: `src/fione/config.py`, `src/fione/db.py` (append a migration), `src/fione/api/app.py`, `src/fione/web/{views,headers,admin_ui}.py`, `src/fione/api/routes_users.py`, `src/fione/web/templates/base.html`, `tests/web/test_routes.py` (a `NOTEBOOK_ROUTES` table for `notebook_ui.router`: 404 disabled, 403 without permission), `src/fione/i18n/{en,ja}.json`, `docs/configuration.md`, `scripts/ui-screenshots.py`
- Test: `tests/unit/test_notebook_service.py`, `tests/unit/test_db.py` (where the `Settings` tests live), `tests/web/test_notebook_ui.py`, `tests/notebook/test_launch_contract.py` (`notebook`)

**Interfaces:**
- Consumes:
  - Task 1: `create_token(..., scope=TokenScope.NOTEBOOK, expires_at=expiry_after(lifetime))` and `revoke_token`.
  - Task 4: `can_use_notebook`.
  - Task 5: the launch-token format and `LAUNCH_PARAM`.
  - Task 7: the launcher HTTP API.
- Produces in `Settings` (each one has a `configuration.md` row):
  - `public_url: str | None` (`FIONE_PUBLIC_URL`, Fione's browser-visible origin; behind a TLS proxy Fione cannot know its scheme).
  - `notebook_url: str | None` (`FIONE_NOTEBOOK_URL`).
  - `notebook_launcher_url: str | None`, `notebook_launcher_secret: str | None`.
  - `notebook_max_lifetime_secs: int = Field(43200, ge=600, le=604800)` (the launcher refuses more than 7 days).
  - Empty strings become None. When `notebook_url` is set, the others are required, both URLs must be bare origins (`scheme://host[:port]`, no path), and they must differ (never the same origin). Otherwise `ValueError`.
  - `Settings.notebooks_enabled` (property) = `notebook_url is not None`.
- Produces the migration `CREATE TABLE notebook_sessions (user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, nonce TEXT NOT NULL, token_id INTEGER NOT NULL REFERENCES api_tokens(id) ON DELETE CASCADE, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT NOT NULL)`. The key is derived, so no key is stored.
- Produces in `notebooks.launch`:
  - `LAUNCH_TOKEN_TTL_SECS = 60`.
  - `launch_key(secret: bytes, user_id: int, nonce: str) -> bytes`.
  - `sign_launch_token(key: bytes, *, user: User, now: float | None = None) -> str`: claims `sub=str(user.id)`, `name=user.username`, `role=user.role.value`, `exp=now+60`, `jti=secrets.token_urlsafe(16)`.
- Produces in `notebooks.launcher`:
  - `NotebookState = Literal["absent", "starting", "running"]`.
  - `LauncherError(Exception)` with `code: Literal["unreachable", "limit", "exists", "image_missing", "refused"]`.
  - `Launcher` Protocol: `ensure(user_id: int, body: dict) -> NotebookState`, `status(user_id: int) -> NotebookState`, `stop(user_id: int) -> None`.
  - `HttpLauncher(url: str, secret: str, timeout: float = 10.0)` (stdlib `urllib.request`; no new runtime dependency). `app.state.notebook_launcher` is set in `create_app` when enabled; tests replace it with a `FakeLauncher`.
- Produces in `notebooks.service`:
  - `state(conn, launcher, user: User) -> NotebookState`: an `absent` state with a session row revokes the token and deletes the row (culled or expired container).
  - `start(conn, launcher, settings, secret: bytes, user: User) -> NotebookState`: if running or starting with a session, it just returns. Otherwise it creates a new nonce, a notebook token and a session row, then calls `ensure`. `exists` → `stop`, then `ensure` once. On any `LauncherError` it revokes the token and deletes the row before re-raising.
  - `stop(conn, launcher, user_id: int) -> None`: launcher `stop`, revoke the token, delete the row.
  - `stop_unless_allowed(conn, launcher, user_id: int) -> None`.
  - `launch_url(conn, settings, secret, user: User) -> str` = `f"{notebook_url}/user/{uid}/login?launch={token}&next=/user/{uid}/lab"`. It raises `NotebookNotRunning` without a session.
- Produces the UI:

| Route | Behaviour |
|---|---|
| `GET /notebook` | 404 when disabled; 403 page without permission (`signed_in`, then `can_use_notebook`). States: `absent` (Start button), `starting` (status partial polled with HTMX every 2 s), `running` (iframe). The launch token is minted only here, when the iframe is rendered. Launcher down → 503 page with `notebook.unavailable`. Launcher text is never rendered; codes map to i18n keys. |
| `GET /notebook/status` | the partial; when running it answers with `HX-Refresh: true` |
| `POST /notebook/start`, `POST /notebook/stop` | `form_auth` (Origin + CSRF), then permission; 303 to `/notebook`. `limit` → the page with `notebook.limit` |

- Produces the CSP hook: a view sets `request.state.csp_frame_src = <notebook origin>`, and `UIHeaders` appends `; frame-src <origin>` to `CONTENT_SECURITY_POLICY` for that response only (in `UIHeaders` itself; `ui_headers()` is also used for the 500 page and stays unchanged). `frame-ancestors 'none'` stays.
- Produces navigation and revocation:
  - Main nav gets a "Notebook" link (`nav="notebook"` for `aria-current`) when enabled and `can_use_notebook`. `render()` has no connection: only when notebooks are enabled, it opens a short-lived one through `request.app.state.db_path` (as `_signed_in` does), so a disabled install pays nothing.
  - `stop_unless_allowed` runs after the API's `PATCH /users/{id}` and the admin UI's notebook/role changes.
  - `stop` runs before `delete_user` in both.
  - Launcher errors there are logged and do not fail the user change; the token is still revoked.

- [ ] **Step 1: Write the failing tests** (`FakeLauncher` records calls and holds states). The launcher is configured with `make_client(notebook_url="http://127.0.0.1:8888", public_url="http://127.0.0.1:8080", notebook_launcher_url="http://launcher", notebook_launcher_secret="x"*32)`.
  - `test_settings_validation`: `notebook_url` without `public_url` → `ValueError`; the same origin for both → `ValueError`; `http://h:8888/path` → `ValueError`; all unset → disabled.
  - `test_page_404_when_disabled_and_403_without_permission`, plus no nav link in either case.
  - `test_start_requires_csrf_and_same_origin`: without CSRF → 403, foreign `Origin` → 403, and `FakeLauncher.calls == []`.
  - `test_start_creates_a_notebook_token_and_session`: the token is `scope == "notebook"` and its `expires_at` is about now + 43200 s (±5 s). The PUT body has the exact keys `launch_key`, `cookie_secret`, `token`, `fione_origin == "http://127.0.0.1:8080"` and `expires_at`. Its `launch_key` equals `launch_key(secret, uid, nonce).hex()`.
  - `test_running_page_frames_the_gateway`: the iframe `src` starts `http://127.0.0.1:8888/user/<uid>/login?launch=v1.`. The CSP has `frame-src http://127.0.0.1:8888` and still `frame-ancestors 'none'`. `Cache-Control: no-store`.
  - `test_other_pages_have_no_frame_src`: `/`, `/account` and `/admin/users` have no `frame-src`.
  - `test_launch_token_is_fresh_per_render`: two GETs → two different `jti`.
  - `test_absent_with_session_revokes_the_token`: the fake goes absent → GET → the old token is 401 on `/api/v1/projects`.
  - `test_stop_revokes_and_removes`.
  - `test_revoking_permission_stops_the_container`: admin PATCH `notebook=none` → `FakeLauncher.stop` is called and the token is 401. Demoting an admin with stored `none` does the same. Deleting the user calls `stop` first.
  - `test_launcher_errors_are_not_rendered_verbatim`: the fake raises `LauncherError("limit")` with a message `<script>` → the page shows `notebook.limit` text and no `<script>`.
  - `test_no_token_in_fione_logs`: with `caplog` over start + render, neither the notebook token nor the launch token appears.
- [ ] **Step 2: Write the failing contract test** `tests/notebook/test_launch_contract.py`: `fione_notebook.auth.verify_launch_token(launch_key(secret, 7, nonce), sign_launch_token(...), owner="7")` returns the claims. A different nonce → None.
- [ ] **Step 3:** Run `uv run pytest tests/unit/test_notebook_service.py tests/web/test_notebook_ui.py -q` and `uv run pytest -m notebook tests/notebook/test_launch_contract.py -q`. Expected: FAIL.
- [ ] **Step 4:** Implement. Add the `notebook.*` i18n keys in both languages and the `configuration.md` rows. In `ui-screenshots.py`, cover the notebook page in the `absent` and `starting` states with a ~20-line stdlib stub launcher the script starts. The running state is captured by Task 10.
- [ ] **Step 5:** Run `uv run pytest -q`, then `uv run pytest -m notebook -q`. Expected: all pass. Ruff clean.
- [ ] **Step 6:** Commit "Add the notebook page: start, stop and a signed-in JupyterLab frame".

### Task 9: Gateway, relay and the Compose profile

**Files:**
- Create: `docker/notebook-gateway.conf`
- Modify: `docker/compose.yaml`, `docker/compose.e2e.yaml`, `docker/.env.example`, `docker/e2e.env`, `scripts/docker-smoke.sh`, `docs/configuration.md` (compose rows), `.github/workflows/ci.yml` (the e2e job builds with `--profile notebook` and runs `uv run pytest -m docker -q` after the build)
- Test: `tests/unit/test_compose.py`, `tests/docker/test_gateway.py` (`docker`)

**Interfaces:**
- Consumes: Task 6 image, Task 7 launcher (`/health`, its env), Task 8 settings.
- Produces the compose services. Everything new is `profiles: ["notebook"]` except the networks and `fione`'s settings.

| Service | Networks | Notes |
|---|---|---|
| `fione` | `backend`, `gateway`, `launcher` | env `FIONE_PUBLIC_URL: ${FIONE_PUBLIC_URL:-}`, `FIONE_NOTEBOOK_URL: ${FIONE_NOTEBOOK_URL:-}`, `FIONE_NOTEBOOK_LAUNCHER_URL: http://notebook-launcher:8000`, `FIONE_NOTEBOOK_LAUNCHER_SECRET: ${FIONE_NOTEBOOK_LAUNCHER_SECRET:-}`, `FIONE_NOTEBOOK_MAX_LIFETIME_SECS: ${FIONE_NOTEBOOK_MAX_LIFETIME_SECS:-43200}` (`:-`, never `:?`: Compose interpolates profile-only services too) |
| `notebook-gateway` | `gateway`, `notebooks` | pinned `nginxinc/nginx-unprivileged:<x.y.z>-alpine` (newest tag at least two weeks old, recorded in the file); `ports: ["127.0.0.1:${FIONE_NOTEBOOK_PORT:-8888}:8080"]`; config mounted read-only; `cap_drop: [ALL]`, `read_only: true`, tmpfs `/tmp` |
| `notebook-launcher` | `launcher` | built from `docker/Dockerfile.launcher`; `/var/run/docker.sock` mounted (the only socket mount); no ports; `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, `read_only: true`; env `FIONE_LAUNCHER_SECRET: ${FIONE_NOTEBOOK_LAUNCHER_SECRET:-}`, `FIONE_NOTEBOOK_IMAGE: ghcr.io/codelibs/fione-notebook:${FIONE_IMAGE_TAG:-dev}`; healthcheck `/health` |
| `notebook-image` | none (`network_mode: none`) | builds `docker/Dockerfile.notebook` with `image:` = the launcher's image name; `scale: 0` so `up --wait` never starts it (check this in the smoke run; if Compose still creates it, use `entrypoint: ["true"]` and name services explicitly in `up`); it exists so `--profile notebook build` builds the image |

  - Networks: `notebooks` and `launcher` are `internal: true`. `gateway` is not, because a published port needs a non-internal network.
- Produces `notebook-gateway.conf`:
  - `log_format` is `$remote_addr [$time_local] "$request_method $uri" $status $body_bytes_sent`, with no `$request`, `$args` or `$http_referer`.
  - The `map` that strips `fione_session` from `Cookie`, and the `map` for `Upgrade`/`Connection`.
  - `resolver 127.0.0.11 valid=10s ipv6=off`.

| Server | Location (in this order) | Behaviour |
|---|---|---|
| `:8080` public | `~ "^/user/[0-9]{1,18}/login$"` | proxy (below) with `error_log /dev/stderr crit` (a 502 would log the query string) |
| | `~ "^/user/[0-9]{1,18}/lab/api/(settings\|workspaces)(/\|$)"` | `limit_except GET { deny all; }`, then proxy |
| | `~ "^/user/(?<uid>[0-9]{1,18})/"` | `set $up nb-$uid; proxy_pass http://$up:8888`; `Host $http_host`; `Cookie $nb_cookie`; WebSocket upgrade; `proxy_read_timeout 1h`; `proxy_buffering off`; `client_max_body_size 100m` |
| | `/` | 404 |
| `:8081` relay (not published) | `~* "^/api/v1/(auth\|tokens\|users)(/\|$)"` | 403 |
| | `/api/v1/` | 401 unless `$http_authorization` matches `^Bearer\s+\S`; `proxy_pass http://fione:8080`; `X-Forwarded-For $remote_addr` (overwrite, never append); `X-Forwarded-Host ""`; `X-Forwarded-Proto ""`; `Cookie ""`; `client_max_body_size 1100m`; `proxy_request_buffering off`; `proxy_read_timeout 300s` |
| | `/` | 404 |

- [ ] **Step 1: Write the failing unit test** `tests/unit/test_compose.py`, which parses `docker/compose.yaml` with `yaml.safe_load` (PyYAML comes with optuna).
  - `test_network_membership`: the service → network sets in the table above. `fione` is not on `notebooks`. `notebooks` and `launcher` are internal.
  - `test_only_the_launcher_mounts_the_socket`: across all services.
  - `test_launcher_publishes_nothing_and_gateway_binds_localhost`.
  - `test_notebook_services_are_in_the_profile`.
  - `test_no_required_interpolation_in_profile_services`: no `:?` in the notebook services' values.
  - `test_gateway_conf_has_no_query_in_logs`: no `$request ` / `$args` / `$request_uri` in a `log_format` line.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_compose.py -q` → FAIL. Implement compose, the config, `.env.example` (`FIONE_NOTEBOOK_PORT`, `FIONE_NOTEBOOK_URL`, `FIONE_PUBLIC_URL`, `FIONE_NOTEBOOK_LAUNCHER_SECRET`, generated with `openssl rand -hex 32`) and `e2e.env` (public test values). Add the compose rows to `configuration.md`. Run `uv run pytest tests/unit/test_compose.py tests/unit/test_docs.py -q` → pass.
- [ ] **Step 3: Write the docker gateway test** `tests/docker/test_gateway.py`. It uses a throwaway network set and the gateway container with the real config. Two stdlib echo servers stand in, with the network aliases `fione` (on `gateway`) and `nb-7` (on `notebooks`); each records the request line and headers it received.
  - `test_relay_denies`, parametrized:
    - `/api/v1/tokens`, `/api/v1/tokens/`, `/api/v1/%74okens`, `/API/V1/TOKENS`
    - `/api/v1//users`, `/api/v1/./auth/login`, `/api/v1/projects/..%2F..%2Ftokens`, `/api/v1/projects/%2e%2e/%2e%2e/users`
    - each with a bearer header → 403 or 404, and the `fione` echo saw nothing.
  - `test_relay_requires_bearer`: no header or `Basic` → 401. `Bearer x` on `/api/v1/projects` → proxied.
  - `test_relay_overwrites_forwarding_headers`: a client sending `X-Forwarded-For: 1.2.3.4` and `X-Forwarded-Host: evil` → the echo sees one XFF value equal to the client's container address, no `X-Forwarded-Host`, and no `Cookie`.
  - `test_relay_serves_nothing_else`: `/`, `/login`, `/api/docs` → 404.
  - `test_public_strips_fione_session`: `Cookie: a=1; fione_session=S; b=2` → the `nb-7` echo sees `a=1; b=2`. `my_fione_session=keep` is kept.
  - `test_public_only_proxies_digit_uids`: `/user/abc/`, `/user/7x/`, `/user/../` → 404 and no echo.
  - `test_settings_and_workspaces_writes_are_refused`: `PUT`/`PATCH`/`DELETE`/`POST` on `/user/7/lab/api/settings/x` and `/user/7/lab/api/workspaces/default` → 403; `GET` → proxied.
  - `test_websocket_upgrade_passes`: the echo sees `Upgrade: websocket` and `Connection: upgrade`.
  - `test_logs_have_no_query_strings`: after `GET /user/7/login?launch=SECRETVALUE` (with the echo stopped, to force a 502, and once with it up), `docker logs` of the gateway does not contain `SECRETVALUE`.
- [ ] **Step 4:** Run `uv run pytest -m docker tests/docker/test_gateway.py -q` → pass.
- [ ] **Step 5: Extend `docker-smoke.sh`.**
  - It builds and starts with `--profile serving --profile notebook`, and refuses an existing project also by the volume/container label `fione.project=<project>`.
  - Checks: gateway `/` → 404; launcher healthy; `docker network inspect <project>_notebooks` lists no `fione` container; the launcher has no published port.
  - The cleanup trap also removes containers and volumes labelled `fione.project=<project>`.
  
  Run it once: `FIONE_IMAGE_TAG=e2e scripts/docker-smoke.sh` → "docker smoke test passed".
- [ ] **Step 6:** Commit "Add the notebook gateway, API relay and Compose profile".

### Task 10: End-to-end notebook tests

**Files:**
- Create: `tests/e2e/test_notebook.py`
- Modify: `tests/e2e/conftest.py`, `.github/workflows/ci.yml` (the e2e job's build already has `--profile notebook` from Task 9; that job runs on pushes to `v2`/`master` only, so say so in the PR: the `docker` and `e2e` notebook tests do not run on pull requests)

**Interfaces:**
- Consumes: the whole stack. `Stack` gains `notebook_port`. The env adds `FIONE_NOTEBOOK_PORT` (a free port), `FIONE_NOTEBOOK_URL=http://127.0.0.1:<port>` and `FIONE_PUBLIC_URL=http://127.0.0.1:<fione port>` (the same host name for both: `localhost` vs `127.0.0.1` is cross-site). Build, `up` and `down` pass `--profile serving --profile notebook`.
- Produces:
  - `Stack.down()` also removes the containers and volumes labelled `fione.project=<project>` (`docker rm -f` / `docker volume rm` by `--filter label=...`).
  - `Console.expect_error_prefix(prefix: str)`: failed loads under the prefix are expected. It is used **only** for the gateway-refused `.../lab/api/workspaces/` and `.../lab/api/settings/` writes.

- [ ] **Step 1: Write the tests.**
  - `test_a_permitted_user_runs_the_sdk_in_jupyterlab`:
    - The admin grants an editor `run` on the users page. The editor signs in, follows the Notebook nav link, and starts the notebook.
    - The page shows the starting state, then the iframe (≤ 120 s).
    - In `page.frame_locator("iframe")`, create a notebook and run `import fione_sdk; print("projects", len(fione_sdk.Client().projects()))` → the output shows `projects 1` (the editor's seeded project).
    - Screenshot the running page to the artifacts.
    - No console errors except the expected prefixes. If JupyterLab shows an error dialog caused by the refused settings/workspaces writes, the test fails and the implementer stops and reports (Global Constraints).
  - `test_without_permission_there_is_no_link_and_403`.
  - `test_cells_cannot_escape`: run one cell that prints one line per check:
    - `pypi.org:443` and `1.1.1.1:443` connect fails
    - `fione` and `seaweedfs` do not resolve
    - `urllib` `GET http://notebook-gateway:8081/api/v1/auth/me` with the token → 403; `/api/v1/tokens` → 403; `/api/v1/projects` without `Authorization` → 401, with it → 200
    - another user's `http://notebook-gateway:8080/user/<other uid>/api/contents` → 403 (Jupyter refuses non-owners)
    
    Assert each printed line.
  - `test_admin_notebook_is_capped`: an admin's cell `Client().modules()` works, and `POST /api/v1/modules` through the SDK's client raises `FioneError` 403 (`token_scope`).
  - `test_stop_removes_the_container_and_revokes_the_token`: read `FIONE_TOKEN` in a cell (test-only stack). After Stop, `docker ps --filter label=fione.project=<p>` is empty, and that token on `GET /api/v1/projects` from the host → 401.
  - `test_notebook_page_csp`: the response to `/notebook` has `frame-src <notebook url>` and `frame-ancestors 'none'`. The gateway's Jupyter responses have `frame-ancestors 'self' <fione url>`.
- [ ] **Step 2:** Run `uv run pytest tests/e2e -m e2e -v` (the full suite, so the existing flows are proven unaffected by the profile). Expected: all pass.
- [ ] **Step 3:** Commit "Add end-to-end tests for the embedded notebook".

### Task 11: Documentation

**Files:**
- Create: `docs/notebook.md`, `docs/notebook.ja.md`
- Modify: `README.md`, `README.ja.md`, `docs/known-limitations.md`, `docs/configuration.md`, `docs/quickstart.md`, `docs/quickstart.ja.md` (a link only), `docs/migrating-from-v1.md`, `docs/migrating-from-v1.ja.md` (the "planned" Notebook rows become shipped; grep all docs for "Notebook" and "planned"). Docs pages may not contain `/home/<name>` (`test_docs_hold_nothing_private`): write "the notebook's work directory", not `/home/nb/work`, `tests/unit/test_docs.py` (known names also from `src/fione_notebook/*.py`, if a page names `FIONE_NB_*`)

**Interfaces:**
- Consumes: every task's settings, behaviours and measured numbers (the image size from Task 6).

- [ ] **Step 1: Notebook quickstart** (`docs/notebook.md`, with a Japanese counterpart covering the same sections):
  - Enabling: `.env` values, `--profile notebook build` and `up`.
  - Granting permission. Using fione-sdk inside and outside the UI.
  - The topology and same-site rule: the same host name with another port locally, sibling subdomains in production behind HTTPS (`nb.fione.example.com` beside `fione.example.com`), `FIONE_PUBLIC_URL`, `FIONE_NOTEBOOK_URL`.
  - The resource defaults, culling (30 min / 1 h), the 12 h lifetime and no egress (the library set is the image's).
  - Persistence: a per-user volume. Kernels are lost on stop and on a launcher restart. `compose down` stops notebooks, and how to remove the volumes by label.
  - An admin's notebook acts as an editor. Settings and layout are not saved.
- [ ] **Step 2: README (en/ja).** A short "Notebooks" section with a link to the quickstart, and the SDK in one paragraph. **known-limitations (en and the Japanese summary):**
  - The launcher holds the Docker socket, which is root-equivalent on the host; it is opt-in.
  - Notebook containers see `FIONE_TOKEN` and their keys (anyone with Docker on the host can too).
  - A viewer granted notebooks still runs code, with read-only data access.
  - Other users' containers are reachable at TCP level on the notebooks network (each Jupyter refuses non-owners).
  - All users' JupyterLabs share one browser origin. Fione serves nothing user-writable unsandboxed there, but a future Jupyter handler that did would let one notebook user act in another's JupyterLab. Unless per-user subdomains are adopted (open decision), say that notebook users share an origin.
  - The JupyterLab settings and layout are not persisted.
  - Firefox, Safari, rootless Docker and Podman are untested.
  - The notebook image size.
- [ ] **Step 3:** Run `uv run pytest tests/unit/test_docs.py -q` → pass (settings, compose and launcher tables, links, no private data). Grep the diff for home paths and usernames: none.
- [ ] **Step 4:** Commit "Document notebooks and fione-sdk".

---

## Self-Review Notes

- **Spec coverage (6.5):**
  - fione-sdk with datasets, EDA (preview/profile), training, leaderboard and prediction, usable from an external Jupyter: Tasks 2 and 3.
  - Embedded JupyterLab without a second sign-in: Tasks 5 and 8.
  - Authorizer by resource and action: Task 5.
  - Layer 1, a per-user container with limits and no egress: Tasks 7 and 9.
  - Layer 2, data reached only through the user's scoped token: Tasks 1 and 9.
  - Layer 3, Jupyter authorization: Task 5.
  - The launch method decided (launcher, not JupyterHub): Global Constraints.
  - Admins plus explicitly allowed users: Task 4.
  - Existing modules callable from notebooks with the same functions: `run_module`, server side (Task 3).
  - Licences 4.6: Task 6. Tests 10.5: every task, plus Task 10.
- **Open decision for the maintainer, before Task 9:** one notebook origin for all users (ruling 1) means isolation between notebook users rests on Jupyter never serving user-controlled, unsandboxed HTML under `/user/<uid>/`. This plan pins that with read-only Jupyter dirs and tests (Tasks 5, 6). The stronger fix is a per-user notebook subdomain in production (`u<uid>.nb.example.com`, JupyterHub's `subdomain_host` approach); it needs wildcard DNS and TLS. The alternative is to document that notebook users must trust each other. Choose one.
- **Deviations to confirm with the maintainer (PR description):**
  - JupyterLab settings and workspaces writes are refused, so layout and settings are not saved.
  - elkjs and FontAwesome licences in the opt-in image.
  - The launcher image is published too: every image Compose names exists for a tag.
  - matplotlib and scikit-learn are in the notebook image.
  - `FIONE_NOTEBOOK_MAX_RUNNING` defaults to 4.
- **Checked against the Phase 2a code before Task 1:** route keys are prefix-less, route enumeration uses the OpenAPI paths, test basenames are unique, `test_routes.py` tables gain the new routes, the navigation link opens its own short connection, i18n keys use the `users.` prefix, and project share/unshare join the denied routes for notebook tokens. `docker-smoke.sh` also needs the notebook variable names in its allow-list, and `tests/e2e/conftest.py` must pass the notebook port and URLs explicitly.
- **Risks verified in their tasks:**
  - Compose interpolation of profile-only services: `:-` only (Task 9).
  - The `extra_log_scrub_param_keys` trait name (Task 5 log test).
  - The keys of JupyterLab's `third-party-licenses.json` (Task 6).
  - Network aliases resolved by nginx, and socket access as root without capabilities (Task 7 and 9 docker tests).
  - JupyterLab behaviour with refused workspace writes (Task 10).
