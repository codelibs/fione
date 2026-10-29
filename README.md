# Fione

Fione is an open-source AutoML server: upload a CSV in the browser, get a trained model, make
predictions and serve the model as a prediction API. It runs with one `docker compose up`.

This is Fione v2, a rewrite in Python. It no longer depends on Fess, H2O or MinIO.

## Features

- **EasyML wizard** for people new to machine learning: upload → data analysis (the column to
  predict, the input columns, the prediction type, the maximum run time) → run → prediction
  summary with a 1–5 star rating and Fione-kun's comment → predictions as a CSV; the result
  page also shows the reasons for the first rows.
- **AutoML screens** for experts (the detailed view): column statistics and charts,
  correlations, leak warnings, every training setting, the job list, leaderboards, variable
  importance, score history, CV metrics, model export and import.
- **Model explanations**: diagnostics from the cross-validation predictions (confusion matrix,
  per-class metrics, ROC and precision-recall curves, calibration, residuals), importance from
  each column's contributions, partial dependence curves, and each prediction's contributions
  in the UI, the API, batch predictions and Fione Serving. Columns that predict the answer
  suspiciously well are flagged as possible leaks.
- **Its own AutoML engine**: LightGBM, XGBoost, CatBoost and ExtraTrees, tuned with Optuna and
  ensembled, within the run time you set.
- **Fione Serving**: a small prediction API (`/invocations`, `/model`, `/ping`) for any trained
  model, as one shared Docker image and the model files.
- **Users and sharing**: administrators, editors and viewers; projects are shared per user.
  API tokens and a REST API (`/api/v1`) for scripts.
- **Python modules** for data operations (built-in frame operations, k-means, low-rank
  factorization; administrators can upload their own).
- **Notebooks** (opt-in): JupyterLab in a container per user, inside Fione, with the Python
  client `fione-sdk`.
- **Storage** on SeaweedFS or any S3-compatible service; metadata in SQLite.
- English and Japanese, light and dark themes, usable on phones.

## Quick start

```sh
git clone https://github.com/codelibs/fione.git && cd fione
printf 'FIONE_S3_ACCESS_KEY=%s\nFIONE_S3_SECRET_KEY=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 32)" > docker/.env
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
docker compose -f docker/compose.yaml --env-file docker/.env logs fione | grep "Setup token"
# open http://127.0.0.1:8080/ and create the administrator with that token
```

The full walk-through, with a sample dataset: [Quick start](docs/quickstart.md).

## Notebooks

Fione can open JupyterLab in a container of your own, inside its web UI, with no second
sign-in. It is opt-in (the Compose profile `notebook`) and needs two more addresses and a secret in
`docker/.env`; see [Notebooks](docs/notebook.md). The same notebooks, a script or your own
Jupyter can drive Fione with `fione-sdk` (`sdk/`, `pip install ./sdk`): datasets, data
profiles, AutoML training, leaderboards, predictions and Python modules, as pandas frames, with
an API token. See [sdk/README.md](sdk/README.md).

## Documentation

- [Quick start](docs/quickstart.md)
- [Notebooks](docs/notebook.md): JupyterLab and `fione-sdk`
- [Configuration](docs/configuration.md): every setting, reverse proxy, backups of the secret key
- [Fione Serving](docs/serving.md): running a model as a prediction API
- [Moving from v1](docs/migrating-from-v1.md)
- [Known limitations](docs/known-limitations.md)

## Status

This release covers the core: data, analysis, AutoML, models and their explanations,
predictions, serving, jobs, users and sharing, and the opt-in notebooks (JupyterLab and a
Python SDK). **Planned, not in this release**: an LLM assistant (Ollama, by default with
`gemma4:12b-mlx` on a Mac), an MCP server and ONNX export. No images are published yet;
you build them from the repository (a version tag publishes the `fione`, `fione-serving`,
`fione-notebook` and `fione-notebook-launcher` images).

The Java v1 (a Fess plugin) is preserved in this repository's history, before the merge of v2.

**Versioning:** this release is 20.0.0. Fione 13–15 followed Fess's version numbers; v2 no longer depends on Fess, so its numbers are independent and continue from 20.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```sh
uv sync                                   # dependencies, including the dev tools
uv run pytest -q                          # unit, API, web and contract tests
uv run pytest tests/e2e -m e2e            # browser tests against the Compose stack (needs Docker)
uv run pytest -m timing                   # wall-clock time budget and latency checks
uv run pytest -m acceptance               # engine accuracy, size and speed targets (downloads data)
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_licenses.py   # dependency licence check
scripts/docker-smoke.sh                   # build and check the Docker stack
```

The end-to-end tests need Chromium for Playwright once: `uv run playwright install chromium`.

## Licence

Fione is licensed under the [Apache License 2.0](LICENSE).

Dependencies must be under Apache-2.0, MIT, BSD, ISC, PSF or 0BSD; GPL, LGPL, AGPL and
non-commercial licences are not allowed, and anything else is decided case by case.
`scripts/check_licenses.py` checks the installed packages and fails on a forbidden one.

The web UI ships two JavaScript libraries, served from the application itself (no CDN), as
listed in [VENDOR.md](src/fione/web/static/vendor/VENDOR.md):

| Library | Version | Licence |
|---|---|---|
| htmx | 2.0.11 | 0BSD |
| Apache ECharts (with ZRender and parts of d3) | 6.1.0 | Apache-2.0 (ZRender and d3: BSD-3-Clause) |

The Compose stack also runs SeaweedFS (Apache-2.0).
