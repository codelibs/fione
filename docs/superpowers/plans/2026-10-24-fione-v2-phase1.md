# Fione v2 Phase 1 (Core Parity) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Java/Fess/H2O Fione with a Python AutoML server (own engine, SQLite + S3-compatible storage, EasyML/AutoML screens, batch prediction, Python-based serving) that reproduces v1 functionality.

**Architecture:** One FastAPI app (`fione`) serves API and a server-rendered UI. Training/prediction/module jobs run as subprocesses launched by the app and tracked in SQLite. Objects (Parquet datasets, model artifacts) live behind a `Storage` abstraction (`file://` or `s3://`). The serving image (`fione_serving`) is built from the same lockfile and loads Fione-written artifacts.

**Tech Stack:** Python 3.12, FastAPI, Jinja2 + HTMX + ECharts, SQLite (stdlib), pandas + pyarrow, LightGBM / XGBoost / CatBoost / scikit-learn + Optuna, boto3, pytest, Playwright, ruff, uv, Docker Compose, SeaweedFS.

**Spec:** `docs/superpowers/specs/2026-10-24-fione-v2-design.md`

## Global Constraints

- Python 3.12 (XGBoost needs ≥3.12; AutoGluon <3.14). Package manager: `uv`; lockfile committed.
- Dependency licenses: allow Apache-2.0, MIT, BSD, ISC, PSF; forbid GPL/LGPL/AGPL/non-commercial; MPL by explicit exception. Checked in CI (Task 1). gensim is not used.
- Roles: `admin`, `editor`, `viewer` + per-project sharing. Model import and module upload are admin-only. No fixed default password; the first admin is created at first start.
- Time budget: `max_runtime_secs` covers the whole job (prep, search, ensemble, final refit); overrun ≤ 5%.
- Artifact targets at Adult scale (~36k train rows, 14 features): ≤ 100MB, predict 1,000 rows ≤ 0.5s.
- Serving contract: `POST /invocations` `{"instances":[{...}]}` → `{"predictions":[...]}`; binomial/multinomial rows `{"label","index","class_probabilities"}`, regression rows `{"value"}`; a failing row yields `{"exception": msg}` without failing the request. `GET /ping`, `GET /` return empty 200.
- Jobs: subprocesses + SQLite job table; no Redis/Celery. Default concurrent training jobs = 1.
- Uploads: CSV up to ~1GB, converted to Parquet at upload time (streamed, never fully in memory).
- LLM-facing tools (Task 15): schema and statistics only; raw cell values only with an explicit per-call opt-in; read-only plus `propose_training_config`.
- i18n: English and Japanese; every English key must exist in Japanese.
- Docs/CI: GHCR for images. Commit messages are public-safe implementation summaries, no attribution lines, written to a file and committed with `git commit -F`.
- Work on branch `v2`, not `master`.

## Review Focus

Inputs the spec implies but no feature task names; each has a pinned test in the owning task.
1. **Japanese/odd CSVs** — UTF-8 BOM, Shift_JIS, `;` or tab delimiters, blank or duplicate header names, mixed-type columns → ingest succeeds or fails with a clear message (Task 5).
2. **Bad targets and tiny data** — target with missing values, a single class, very high cardinality, fewer than 50 rows with 5 folds → clear error or automatic fold reduction, never a stack trace (Task 7).
3. **Prediction input mismatch** — unseen categories, missing or extra columns, wrong dtypes → per-row `exception` in serving, clear error in batch predict (Tasks 12, 14).
4. **Orphaned and cancelled jobs** — app restart while a job is `running`; cancelling kills the whole process tree, including native threads (Task 10).
5. **Hostile names** — Japanese project names, `../` in project/dataset/module names, oversized uploads → safe IDs, no path escape (Tasks 5, 16).

---

## File Structure

```
pyproject.toml, uv.lock, ruff.toml, .github/workflows/{ci,nightly}.yml
scripts/check_licenses.py
src/fione/
  config.py db.py version.py
  storage/{base,local,s3}.py
  auth/{passwords,tokens,roles,service}.py
  projects/{service,ingest}.py
  data/{profile,frames}.py
  engine/{config,events,prep,families,search,ensemble,automl,artifact}.py
  jobs/{store,runner,worker,handlers}.py
  predict/batch.py
  models/service.py            # leaderboard rows, export/import
  modules/{registry,frame_ops,unsupervised}.py
  tools/{registry,builtin}.py  # LLM-facing typed tools
  api/{app,deps,schemas}.py + api/routes_{auth,projects,datasets,jobs,models,predict,modules,system}.py
  web/{views.py,templates/,static/}   # Jinja2 + HTMX + ECharts
  i18n/{en,ja}.json, i18n/__init__.py
src/fione_serving/{app,loader}.py
docker/{Dockerfile,Dockerfile.serving,compose.yaml,compose.e2e.yaml}
tests/{unit,api,contract,e2e,acceptance}/
```
Removed in Task 0: all v1 Java/Maven/DBFlute files (`src/main`, `src/test`, `pom.xml`, `dbflute_fione/`, `mydbflute/`, `tools/`, `deps.xml`, `dbflute.xml`).

---

### Task 0: Branch, v1 removal, Python scaffold

**Files:** Create `pyproject.toml`, `ruff.toml`, `src/fione/__init__.py`, `src/fione/version.py`, `tests/unit/test_smoke.py`, `.github/workflows/ci.yml` (lint + unit). Delete v1 files listed above. Modify `README.md`, `.gitignore`.

**Interfaces:** Produces `fione.version.__version__: str`.

- [ ] **Step 1 (done by the controller before dispatch):** branch `v2` exists, tag `v1-final` points at `master` (local only, not pushed). Leave the untracked `dbflute_fess/`, `freegen.sh`, `memo.txt`, `release.sh`, `tmp/` untouched. Also delete the v1 workflow `.github/workflows/maven.yml`.
- [ ] **Step 2:** Confirm `git branch --show-current` is `v2`.
- [ ] **Step 3: Failing test** `test_version_is_semver`: `re.fullmatch(r"\d+\.\d+\.\d+", __version__)`. Run `uv run pytest tests/unit -q` → FAIL (module missing).
- [ ] **Step 4:** Remove v1 files, scaffold `pyproject.toml` (project `fione`, `requires-python = ">=3.12,<3.14"`, src layout, dev group: pytest, pytest-cov, ruff, playwright), `ruff.toml`, version `2.0.0.dev0`. Rewrite `README.md` (Apache license kept).
- [ ] **Step 5:** `uv run pytest -q && uv run ruff check .` → PASS. Commit "Start Fione v2: Python scaffold, remove v1 sources".

### Task 1: License checker

**Files:** Create `scripts/check_licenses.py`, `tests/unit/test_check_licenses.py`; modify `ci.yml`.

**Interfaces:** Produces `check_licenses.classify(license_expr: str) -> Literal["allowed","forbidden","review"]` and CLI exit code 1 if any installed dependency is `forbidden`.

- [ ] Tests: `classify("Apache-2.0")=="allowed"`, `"MIT License"`, `"BSD-3-Clause"` allowed; `"GPL-3.0"`, `"LGPL-2.1"`, `"AGPL-3.0"` forbidden; `"MPL-2.0"` → `review`; `"Apache-2.0 OR GPL-2.0"` → `allowed` (any permitted alternative).
- [ ] Implement with `importlib.metadata` (License field and Trove classifiers). Keep an `EXCEPTIONS` dict (package → reason) in the script. Add CI step `uv run python scripts/check_licenses.py`.
- [ ] Run against the real environment; fix or document each `review`/`forbidden` result. Commit.

### Task 2: Settings and SQLite

**Files:** Create `src/fione/config.py`, `src/fione/db.py`, `tests/unit/test_db.py`.

**Interfaces:**
- Produces `Settings(BaseSettings)` with `data_dir: Path`, `storage_url: str`, `s3_endpoint/access_key/secret_key/region`, `secret_key_path: Path`, `max_concurrent_train_jobs: int = 1`; `get_settings() -> Settings` (cached); `load_secret(settings) -> bytes` (creates a random 32-byte key file with mode 0600 if missing).
- Produces `db.connect(path: Path) -> sqlite3.Connection` (WAL, foreign keys on, `row_factory=sqlite3.Row`), `db.migrate(conn) -> int` (applies the ordered `MIGRATIONS: list[str]`, returns schema version).

- [ ] Tests: `migrate` twice is idempotent; version equals `len(MIGRATIONS)`; `load_secret` returns the same bytes on the second call and the file mode is `0o600`; env `FIONE_DATA_DIR` overrides the default.
- [ ] Implement. `MIGRATIONS` starts with one migration creating only a `schema_meta` table; each task that owns tables (`users`/`api_tokens` Task 4, `projects`/`project_members`/`datasets` Task 5, `jobs`/`job_events` Task 10, `models` Task 11, `modules` Task 16) appends its own migration and never edits earlier ones. `Settings` also has `image_tag: str = "dev"` (env `FIONE_IMAGE_TAG`), used by Tasks 9, 11, 14. Commit.

### Task 3: Storage abstraction

**Files:** Create `src/fione/storage/{base,local,s3}.py`, `tests/unit/test_storage.py`.

**Interfaces:** Produces `Storage` Protocol — `put(key: str, data: bytes | BinaryIO) -> None`, `get(key) -> bytes`, `open_read(key) -> BinaryIO`, `exists(key) -> bool`, `list(prefix) -> list[str]`, `delete(key) -> None`, `delete_prefix(prefix) -> None`, `size(key) -> int`; `open_storage(settings: Settings) -> Storage` chooses by `storage_url` scheme (`file://`, `s3://bucket`).

- [ ] Tests parametrized over backends via one shared `storage` fixture: put/get round trip; `list("a/")` returns only keys under the prefix; `delete_prefix` removes nested keys; `get` of a missing key raises `KeyError`; keys containing `..` or starting with `/` raise `ValueError` (both backends).
- [ ] Local backend uses `pathlib` under a root and validates keys. S3 backend uses `boto3` with path-style addressing, multipart for streams. S3 tests carry `@pytest.mark.s3` and run only when `FIONE_TEST_S3_ENDPOINT` is set.
- [ ] Verify against a real SeaweedFS container (single-container S3 mode) with `pytest -m s3`; record the exact working image/command in `docker/compose.s3-test.yaml` (one `seaweedfs` service), which Task 19 reuses in `docker/compose.yaml`. Commit.

### Task 4: Authentication and roles

**Files:** Create `src/fione/auth/{passwords,tokens,roles,service}.py`, `tests/unit/test_auth.py`.

**Interfaces:**
- `hash_password(pw: str) -> str` / `verify_password(pw: str, hashed: str) -> bool` (`hashlib.scrypt`, per-user salt).
- `Role(StrEnum)`: `ADMIN`, `EDITOR`, `VIEWER`; `ProjectAccess(StrEnum)`: `OWNER`, `EDITOR`, `VIEWER`.
- `service.create_user(conn, username: str, password: str, role: Role) -> User`; `authenticate(conn, username, password) -> User | None`; `needs_first_admin(conn) -> bool`; `issue_token(conn, user_id: int, name: str) -> str` (plaintext returned once; sha256 stored); `user_from_token(conn, token: str) -> User | None`; `revoke_token(conn, token_id: int)`.
- `roles.can_access_project(conn, user: User, project_id: str, need: Literal["read","write"]) -> bool`; `roles.require_admin(user)` raises `PermissionError`.

- [ ] Tests: wrong password → `None`; duplicate username → `ValueError`; token verifies once issued and not after `revoke_token`; viewer `write` → False, `read` on a shared project → True; non-member → False on both; admin → True on all; `needs_first_admin` True on an empty DB and False after the first `create_user(..., Role.ADMIN)`.
- [ ] Implement; usernames limited to `[A-Za-z0-9._-]{1,64}`. Commit.

### Task 5: Projects and dataset ingest

**Files:** Create `src/fione/projects/{service,ingest}.py`, `tests/unit/test_projects.py`, `tests/unit/test_ingest.py`.

**Interfaces:**
- `DatasetType(StrEnum)`: `TRAIN`, `TEST`, `PREDICT`.
- `service.create_project(conn, owner: User, name: str) -> Project` (id = `slugify(name)` + short random suffix; Japanese names keep the display name and get an ASCII-safe id); `list_projects(conn, user) -> list[Project]`; `delete_project(conn, storage, user, project_id)`; `share_project(conn, owner, project_id, username, access: ProjectAccess)`.
- `ingest.ingest_csv(storage, conn, project_id: str, name: str, type: DatasetType, stream: BinaryIO, *, max_bytes: int = 2**30) -> Dataset` — detects encoding (UTF-8, UTF-8-BOM, Shift_JIS/CP932, EUC-JP) and delimiter, streams with `pyarrow.csv.open_csv`, writes Parquet to `projects/<id>/datasets/<dataset_id>/data.parquet`, records row/column counts and schema.
- `ingest.read_dataset(storage, dataset: Dataset, columns: list[str] | None = None) -> pd.DataFrame`; `ingest.export_csv(storage, dataset) -> Iterator[bytes]`.

- [ ] Tests (Review Focus 1, 5): BOM-prefixed UTF-8, a CP932-encoded file with Japanese headers, `;` and tab delimiters ingest to the same frame; blank/duplicate headers become `column_1`, `name`, `name_2`; a mixed int/str column is read as string; a stream larger than `max_bytes` raises `ValueError("too large")` and leaves no partial objects; project name `"../../etc"` yields an id with no path separators; `delete_project` removes all objects under the prefix; sharing gives a viewer read but not write access.
- [ ] Implement; wrap CSV parse errors in `IngestError(message)` with a user-readable message. Commit.

### Task 6: Profiling (EDA) and frame utilities

**Files:** Create `src/fione/data/{profile,frames}.py`, `tests/unit/test_profile.py`.

**Interfaces:**
- `ColumnProfile` dataclass: `name, kind ("numeric"|"categorical"|"text"|"datetime"|"id"|"constant"), missing_rate: float, n_unique: int, stats: dict | None (mean/std/min/q25/median/q75/max), histogram: list[tuple[float, int]] | None, top_values: list[tuple[str, int]] | None, outlier_rate: float | None`.
- `DatasetProfile` dataclass: `n_rows, n_cols, columns: list[ColumnProfile], correlations: list[tuple[str, str, float]] (top 20 by |r|), leak_suspects: list[LeakSuspect(column, reason, score)]`.
- `profile_dataset(df: pd.DataFrame, target: str | None = None, *, sample_rows: int = 200_000) -> DatasetProfile`.
- `frames.change_column_type(df, column: str, to: Literal["numeric","categorical","text","datetime"]) -> pd.DataFrame`.

- [ ] Tests: a unique-per-row column is `id`; a column with one value is `constant`; a column equal to the target (or a deterministic function of it) is a `leak_suspect`; outlier rate for `[1]*98 + [1000]*2` is 0.02 (IQR rule); profiling a 1M-row frame uses at most `sample_rows` rows (assert via a spy); `change_column_type(..., "categorical")` yields category dtype.
- [ ] Implement with pandas/numpy only. Commit.

### Task 7: Engine — config, events, preprocessing, search

**Files:** Create `src/fione/engine/{config,events,prep,families,search}.py`, `tests/unit/test_engine_search.py`.

**Interfaces:**
- `TrainConfig` dataclass: `target: str, task: Literal["auto","classification","regression"]="auto", max_runtime_secs: int=3600, max_runtime_secs_per_model: int|None=None, max_models: int|None=None, nfolds: int=5, seed: int=0, balance_classes: bool=False, stopping_rounds: int=3, stopping_metric: str="auto", stopping_tolerance: float=0.001, sort_metric: str="auto", keep_cv_predictions: bool=False, keep_cv_models: bool=False, keep_cv_fold_assignment: bool=False, ignored_columns: list[str]=[]`.
- `Event(type: Literal["started","trial","family_done","ensemble","stopped","finished"], ts: float, data: dict)`; `EventSink = Callable[[Event], None]`.
- `Deadline(total_secs: float)` with `remaining() -> float`, `expired() -> bool`, `child(secs: float) -> Deadline`.
- `prep.Prep` — `fit(df) -> Prep`, `tree(df)`, `catboost(df)`, `dense(df)` (the three views from the spike: category dtype / string categoricals / coded + median-imputed).
- `families.FAMILIES: dict[str, FamilySpec]` for LightGBM, XGBoost, CatBoost, ExtraTrees; `FamilySpec.fit(params, X_tr, y_tr, X_va, y_va, deadline) -> Model` must abort promptly when `deadline.expired()` (LightGBM/XGBoost via callbacks; for CatBoost verify callback support and otherwise chunk iterations).
- `search.run_family(name, X, y, folds, task, deadline, emit, should_stop) -> FamilyResult(oof: ndarray, models: list, best_params: dict, trials: int)`.

- [ ] Tests (Review Focus 2): on `make_classification(50_000, 30)`, running all families with `Deadline(10)` finishes in ≤ 10.5s wall time; a deadline of 2s still returns the best fully completed trial or raises `NoModelError` (never hangs); the target with NaN → `ConfigError("target has missing values")`; single-class target → `ConfigError`; 30 rows with `nfolds=5` → folds auto-reduced and an event `data={"nfolds_reduced_to": n}` emitted; `should_stop=lambda: True` returns promptly with `stop_reason="cancelled"` data in the `stopped` event; each trial emits an `Event("trial", data={"family","score","params","elapsed"})`.
- [ ] Implement per spec 5.1: per-fold deadline checks, Optuna trial timeout/pruning, first trial uses family defaults. Commit.

### Task 8: Engine — ensemble, leaderboard, AutoML facade

**Files:** Create `src/fione/engine/{ensemble,automl}.py`, `tests/unit/test_engine_automl.py`.

**Interfaces:**
- `ensemble.caruana(oof: dict[str, ndarray], y, task, rounds: int = 30) -> dict[str, float]` (weights sum to 1).
- `AutoML(config: TrainConfig, emit: EventSink = ..., should_stop: Callable[[], bool] = ...)`; `.fit(df: pd.DataFrame) -> TrainedModel`.
- `TrainedModel`: `task`, `classes: list | None`, `columns: list[str]`, `leaderboard: pd.DataFrame` (columns `model, family, cv_score, cv_std, train_secs, weight`; sorted by `sort_metric`), `feature_importance: pd.Series`, `stop_reason: str`, `predict(df) -> pd.Series`, `predict_proba(df) -> pd.DataFrame`.
- Behavior: `balance_classes` reweights; `ignored_columns` excluded from features; `max_models` stops the search; `stopping_rounds/tolerance/metric` stop when no improvement across the last N completed trials; `stop_reason ∈ {"time","max_models","no_improvement","cancelled"}`.

- [ ] Tests: iris reaches accuracy ≥ 0.9 on a held-out split; California-like regression returns `predict` floats and `r2 > 0.6`; leaderboard weights sum to 1 and the top row has the best `cv_score`; `max_models=2` → `stop_reason=="max_models"`; ignored column absent from `columns`; `feature_importance` index ⊆ `columns`; predicting a frame with an unseen category does not raise.
- [ ] Implement. Commit.

### Task 9: Engine — artifact format, signing, size caps

**Files:** Create `src/fione/engine/artifact.py`, `tests/unit/test_artifact.py`, `tests/acceptance/test_engine_targets.py`.

**Interfaces:**
- `save_model(model: TrainedModel, storage: Storage, prefix: str, secret: bytes, *, image_tag: str) -> Manifest` writes `manifest.json` (`format_version, fione_version, image_tag, files{name: sha256}, hmac, task, classes, columns, target`) and `model.joblib`, keeping only ensemble members with weight > 0 (fold models of those members only), and caps tree counts/leaves via family params.
- `load_model(storage, prefix, secret: bytes) -> TrainedModel` verifies the HMAC **before** unpickling, else raises `UntrustedArtifactError`.
- `load_model_unverified_hash_only(storage, prefix) -> TrainedModel` (for serving: checks sha256 of files only).

- [ ] Tests: round trip predictions equal; flipping one byte of `model.joblib` → `UntrustedArtifactError` and `joblib.load` is never called (patched spy); wrong secret → error; zero-weight members absent from the saved file list.
- [ ] Acceptance (`@pytest.mark.acceptance`, nightly): on Adult (OpenML `adult` v2), `max_runtime_secs=120` → wall time ≤ 126s, artifact ≤ 100MB, predict 1,000 rows ≤ 0.5s, test accuracy within 0.01 of the spike's 0.876. Fix size/latency in `families.py` params until met; if impossible, stop and report to the user (spec 5.6).
- [ ] Commit.

### Task 10: Job store and runner

**Files:** Create `src/fione/jobs/{store,runner,worker}.py`, `tests/unit/test_jobs.py`.

**Interfaces:**
- `JobStatus(StrEnum)`: `QUEUED, RUNNING, DONE, FAILED, CANCELLED`.
- `store.enqueue(conn, kind: str, project_id: str | None, owner_id: int, payload: dict) -> Job`; `get_job`, `list_jobs(conn, project_id)`, `append_event(conn, job_id, Event)`, `events_since(conn, job_id, after_id: int) -> list[Event]`, `delete_job`, `delete_all_jobs(conn, project_id)`.
- `runner.JobRunner(settings, db_path)` — `start()` (thread polling every 1s; launches `python -m fione.jobs.worker <job_id>` while running < `max_concurrent_train_jobs`; training kinds are counted, short kinds are not), `cancel(job_id)`, `recover_orphans()` (marks `running` jobs with no live process as `FAILED`, message "interrupted by restart"), `stop()`.
- `worker.main(job_id: int)`; `handlers.HANDLERS: dict[str, Callable[[JobContext], None]]` with `JobContext(conn, storage, job, emit, should_stop)`.

- [ ] Tests (Review Focus 4): enqueue → runs a trivial `"echo"` handler → `DONE` with events recorded; two queued training jobs with limit 1 run one after the other; `cancel` of a job whose handler spawns a child process kills both (assert via `psutil`-free check using `os.kill(pid, 0)` raising); `recover_orphans` after a simulated crash flips `RUNNING`→`FAILED`; a handler exception → `FAILED` with the message and traceback in the last event.
- [ ] Implement with `subprocess.Popen(start_new_session=True)` and `os.killpg` for cancel. Commit.

### Task 11: AutoML job handler and model records

**Files:** Create `src/fione/jobs/handlers.py` (automl), `src/fione/models/service.py`, `tests/unit/test_handler_automl.py`.

**Interfaces:**
- Job payload `{"dataset_id": int, "config": TrainConfig-as-dict}`; handler reads the train dataset, runs `AutoML` with `emit=ctx.emit`, `should_stop=ctx.should_stop`, saves via `save_model` to `projects/<p>/models/<model_id>/`, and inserts a `models` row (`id, project_id, dataset_id, job_id, task, target, leaderboard_json, best_model, metrics_json, created_at`).
- `models.service.list_models(conn, project_id) -> list[ModelRecord]`, `get_model(conn, model_id)`, `load_trained(storage, record, secret) -> TrainedModel`, `delete_model(...)`.

- [ ] Tests: end-to-end through `JobRunner` on a small CSV dataset → `DONE`, a model record exists, `load_trained` predicts; payload with an unknown column in `ignored_columns` → job `FAILED` with a readable message; cancelling mid-run leaves no model record and no partial objects.
- [ ] Implement. Commit.

### Task 12: Batch prediction

**Files:** Create `src/fione/predict/batch.py`, extend `handlers.py` (`batch_predict`), `tests/unit/test_batch_predict.py`.

**Interfaces:** `batch_predict(model: TrainedModel, df: pd.DataFrame, include_columns: list[str] | None = None) -> pd.DataFrame` returns `predict` (+ `p_<class>` per class for classification) followed by the selected input columns (all if `None`). Job `batch_predict` payload `{"model_id","dataset_id","include_columns"}` saves a `PREDICT` dataset named `predict_<dataset>`.

- [ ] Tests (Review Focus 3): missing required column → `PredictInputError("missing columns: [...]")` listing them; extra columns are ignored; unseen category yields a prediction (no error); string in a numeric column → `PredictInputError` naming the column; probabilities per row sum to 1 ±1e-6; output row order equals input row order.
- [ ] Implement; commit.

### Task 13: Model export / import

**Files:** Extend `src/fione/models/service.py`, `tests/unit/test_model_export.py`.

**Interfaces:** `export_model(storage, record) -> Iterator[bytes]` (zip of manifest + files); `export_all_models(...)` as a job kind; `import_model(storage, conn, admin: User, project_id, zip_stream, secret) -> ModelRecord` — admin-only; verifies the HMAC unless `trust_foreign=True` (then records `trusted=False` and the UI shows a warning).

- [ ] Tests: non-admin → `PermissionError`; export then import in a fresh instance with the same secret works; tampered zip → `UntrustedArtifactError`; zip with `../` member names → `ValueError`; foreign-signed artifact loads only with `trust_foreign=True`.
- [ ] Implement; commit.

### Task 14: Serving package and bundle

**Files:** Create `src/fione_serving/{app,loader}.py`, `docker/Dockerfile.serving`, `tests/contract/test_serving_contract.py`; modify `src/fione/models/service.py` (bundle).

**Interfaces:**
- `fione_serving.app.create_app(model_dir: Path) -> FastAPI` — `GET /`, `GET /ping` (empty 200), `GET /model` (no Content-Type requirement), `POST /invocations`.
- `/model` returns `{"names","domains","responseColumn","category","nclasses","nfeatures","uuid","instance","engine","fioneVersion"}`; v1's H2O-specific fields (`algoName`, `h2oVersion`, `modelDescriptor`, thresholds) are intentionally dropped.
- Startup refuses (exit 1, clear message) if the manifest `image_tag` differs from the running image's `FIONE_IMAGE_TAG`, or any file sha256 mismatches.
- `models.service.make_serving_bundle(storage, record) -> Bundle(model_zip: bytes, run_command: str)`; `run_command` = `docker run --rm -p 8081:8080 -v <model_dir>:/model ghcr.io/<owner>/fione-serving:<tag>`.

- [ ] Contract tests: iris-shaped model → response exactly `{"predictions":[{"label":"setosa","index":0,"class_probabilities":[...]}]}` with the same key order; regression → `{"value": float}`; a batch with one bad row (string in numeric column) returns 200 with that row `{"exception": "..."}` and others intact; non-JSON body → 400; corrupted model file → startup failure (test via `create_app` raising `ModelLoadError`).
- [ ] Dockerfile.serving: non-root user, no shell echo tricks, `CMD ["python","-m","fione_serving"]`, built from the same `uv.lock`. Commit.

### Task 15: LLM-facing typed tools

**Files:** Create `src/fione/tools/{registry,builtin}.py`, `tests/unit/test_tools.py`.

**Interfaces:**
- `Tool(name: str, description: str, parameters: dict /* JSON Schema, flat */, read_only: bool, fn: Callable[[ToolContext, dict], dict])`.
- `ToolContext(conn, storage, user: User, allow_samples: bool = False)`; `registry.list_tools() -> list[dict]` (OpenAI `tools` format); `registry.call_tool(name: str, args: dict, ctx: ToolContext) -> dict` validates args against the schema, enforces project access, logs the call.
- Built-ins: `describe_dataset(dataset_id)`, `get_column_stats(dataset_id, column)`, `get_leaderboard(model_id)`, `get_feature_importance(model_id)`, `get_training_events(job_id, last_n=50)`, `propose_training_config(dataset_id, target, notes)` → returns a validated `TrainConfig` dict marked `{"proposal": true}` (never starts a job).

- [ ] Tests: a dataset containing the sentinel value `"SECRET-CELL-VALUE"` never appears in any tool result when `allow_samples=False` (including category top values); with `allow_samples=True` only truncated (≤ 50 chars) values appear; columns beyond 200 are summarized, not listed; unknown tool or schema-invalid args → `ToolError`; a viewer-owned-nothing user calling a tool on another's project → `PermissionError`; `propose_training_config` with an invalid target → `ToolError`; no built-in has `read_only=False`.
- [ ] Implement; commit.

### Task 16: Python modules (frame ops, unsupervised)

**Files:** Create `src/fione/modules/{registry,frame_ops,unsupervised}.py`, extend `handlers.py` (`module`), `tests/unit/test_modules.py`.

**Interfaces:** `Module` dataclass: `id, name, kind ("frame"|"train"|"predict"), params: dict /* JSON Schema */, run: Callable[[pd.DataFrame, dict], pd.DataFrame]`. `registry.builtin_modules() -> list[Module]`: frame ops `cbind, concat, cor, cslice, fillna, floor, pivot, rbind, replace, rslice, sort, split, tokenize`; `kmeans` train/predict (scikit-learn `KMeans`); `lowrank` train/predict (TruncatedSVD, NMF option) replacing GLRM. `registry.load_user_module(path: Path) -> Module` for uploaded files exposing `MODULE = {...}` and `run(df, params)`; `registry.reload()`.

- [ ] Tests: one parametrized test per frame op with a 5-row frame and the expected output; `kmeans` train then predict assigns the same cluster ids on the training data; `lowrank` output has `n_components` columns; uploading a user module as non-admin → `PermissionError`; a module path or id containing `../` → `ValueError`; a user module runs only inside the `module` job subprocess (assert the API process never imports it).
- [ ] Implement; commit.

### Task 17: REST API

**Files:** Create `src/fione/api/{app,deps,schemas}.py`, `src/fione/api/routes_{auth,projects,datasets,jobs,models,predict,modules,system}.py`, `tests/api/test_*.py`.

**Interfaces:** `create_app(settings: Settings | None = None) -> FastAPI`; deps `current_user`, `require_role(Role)`, `project_access(need)`. Auth via signed session cookie (UI) or `Authorization: Bearer <token>`. Routes under `/api/v1`: `POST /auth/login|logout|first-admin`, `GET/POST /users` (admin), `POST /tokens`; `GET/POST/DELETE /projects`, `POST /projects/{id}/share`; `GET/POST/DELETE /projects/{id}/datasets`, `GET .../datasets/{d}/download|profile|columns/{c}`; `POST /projects/{id}/jobs/automl|batch-predict`, `GET /jobs`, `GET /jobs/{id}/events?after=`, `POST /jobs/{id}/cancel`, `DELETE /jobs`; `GET /projects/{id}/models`, `GET /models/{id}`, `GET /models/{id}/export|serving`, `POST /projects/{id}/models/import` (admin); `GET/POST /modules` (upload admin); `GET /system/status`.

- [ ] Tests: a permission matrix test iterates every route × {anonymous, viewer, editor, admin, non-member} and asserts the expected status code from one table in the test file; first-admin endpoint returns 409 after the first admin exists; a 5MB upload streams without loading into memory (spy on `read()` sizes); login failure returns 401 with no user-enumeration difference.
- [ ] Implement; start `JobRunner` and `recover_orphans()` in the app lifespan. Commit.

### Task 18: Web UI

Four deliverables, each its own commit and reviewable on its own. Stack: Jinja2 templates, HTMX for partial refresh (job progress polling every 2s), ECharts for charts. **Design (user-approved: modern UI/UX redesign):** a small hand-written design system in `web/static/css/` — CSS-variable design tokens, light and dark themes (`prefers-color-scheme` plus a manual toggle), responsive down to phone width, visible focus states, WCAG AA contrast, no heavy UI framework. EasyML is one purpose per screen with a step indicator; AutoML detail screens are dense but scannable (tables, tabs). Keep the v1 terms and main flow. 18a also delivers the layout, components (button, card, table, tabs, form field, toast, empty state) and a `/_design` page listing them. Tests: API-level HTML tests with `TestClient` (status + key text) and Playwright in Task 20.

**18a — Shell, auth, i18n.** Files: `web/views.py`, `web/templates/{base,login,first_admin}.html`, `i18n/{__init__,en,ja}.json`, `tests/unit/test_i18n.py`. Interface: `i18n.t(key: str, lang: str, **vars) -> str`; language from user setting, then `Accept-Language`. Tests: every key in `en.json` exists in `ja.json` and vice versa; missing key falls back to English; `/login` renders in Japanese for `Accept-Language: ja`.
**18b — EasyML wizard.** Screens: project dashboard, upload (Training Data), data analysis (predicted column, input columns, prediction type, 最大実行時間, 実行), job progress, 予測結果サマリー (best model, star rating from the CV score, model count, Fione-kun message, links to predict and serving), new prediction (test CSV, choose output columns, download `predict_*.csv`). Tests: the iris flow through HTML endpoints with the runner in-process ends on the summary page with a star rating 1–5.
**18c — AutoML detail screens.** Dataset/column views (profile charts), full training parameter form (spec 5.4), job list (cancel, delete, delete all), leaderboard, model page (variable importance, per-trial score history, CV metrics via ECharts), datasets of types train/test/predict, model export/import (admin), serving bundle download, Python modules (admin). The per-user "simple/detailed" toggle is a user preference, not a permission.
**18d — Admin and system.** Users and tokens, role assignment, system status (job queue, storage health, LLM connection placeholder).

- [ ] For each of 18a–18d: write the HTML tests listed, run → FAIL, implement, run → PASS, commit.

### Task 19: Docker and Compose

**Files:** Create `docker/Dockerfile`, `docker/compose.yaml`, `docker/compose.e2e.yaml`, `.dockerignore`.

**Interfaces:** Compose services `fione` (port 8080, volume `fione-data:/data`) and `seaweedfs` (S3 on 8333, path-style, volume `seaweed-data`), with the working SeaweedFS command recorded in Task 3. `fione` waits for storage health. Ollama and Jupyter services are added by their own phases. The image tag is `ghcr.io/<owner>/fione:<version>`; `FIONE_IMAGE_TAG` is baked in for both images.

- [ ] Verify: `docker compose -f docker/compose.yaml up -d --build`, then `curl -f localhost:8080/api/v1/system/status` → 200; `down -v` leaves nothing. Commit.

### Task 20: E2E, CI and nightly

**Files:** Create `tests/e2e/{conftest,test_easyml_flow,test_serving_flow,test_permissions}.py`, `.github/workflows/nightly.yml`; modify `ci.yml`.

- [ ] E2E (Playwright, against `compose.e2e.yaml`): first-admin setup → upload `iris.csv` → data analysis → 実行 (`最大実行時間` 60s) → summary shows a star rating → new prediction with a 3-row CSV → download `predict_*.csv` contains 3 rows and `p_*` columns → serving page shows the `docker run` command → run the serving image with the downloaded model and `POST /invocations` returns the contract shape. Permissions test: a viewer sees no 実行 button and gets 403 on the API.
- [ ] CI: PR → lint, unit, api, contract, license check; push to `v2`/`master` → e2e; nightly → `pytest -m acceptance`. Publish `fione` and `fione-serving` images to GHCR on tags.
- [ ] Run everything locally once (`uv run pytest -q && uv run pytest tests/e2e`) and record the results in the PR description. Commit.

### Task 21: Documentation

**Files:** Modify `README.md`; create `docs/quickstart.md`, `docs/quickstart.ja.md`, `docs/serving.md`.

- [ ] Quick start (compose up, first admin, iris), serving usage with the exact `docker run`, configuration table (every `FIONE_*` setting), the `/model` contract difference from v1, and a v1 → v2 notes page (no H2O model migration; CSV re-upload). Commit.

---

## Self-Review Notes

- **Spec coverage:** 4.1–4.6 → Tasks 2–4, 10, 19; 5.1–5.7 → Tasks 7–9; 6 (EDA) → Task 6; 7 parity table → Tasks 5, 11–13, 16, 18; 8 serving → Task 14; 9 tools → Task 15; 10.5 tests → every task plus Task 20. Deferred by design: SHAP/`contributions`, Notebook, assistant UI, Ollama (Phases 2–3), MCP, v1 CSV import.
- **Known deviation to confirm with the user:** `GET /model` drops H2O-specific fields (Task 14); spec 8 says "maintain the contract."
- **Risks:** CatBoost deadline callbacks (Task 7), SeaweedFS command (Task 3), and the Adult-scale size/latency targets (Task 9) are verified in their tasks; failing Task 9 triggers the spec 5.6 stop-and-report rule.
