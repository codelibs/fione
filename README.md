# Fione

Fione is an open-source AutoML server that makes predictions your AI can use. Train a model from a
CSV, then use its predictions from AI tools such as Claude or Codex over MCP, from your own
service through the REST API or Fione Serving, or in the browser. It runs on your own server with
one `docker compose up`, and no machine-learning expertise is needed.

Documentation: [fione.codelibs.org](https://fione.codelibs.org/) (English) and
[fione.codelibs.org/ja/](https://fione.codelibs.org/ja/) (Japanese).

## Features

- **Use it from AI tools**: with MCP switched on, MCP clients such as Claude Code, Claude Desktop
  or Codex can create a project, upload a CSV, train, wait for the job, read the leaderboard and
  predict on your Fione server. They bring their own language model: Fione needs none for
  this. See [MCP](docs/mcp.md) and the [guide](https://fione.codelibs.org/guide/mcp.html).
- **EasyML wizard** for people new to machine learning: upload → data analysis (the column to
  predict, the input columns, the prediction type, the maximum run time) → run → prediction
  summary with a 1–5 star rating and a plain-language explanation of the score →
  predictions as a CSV; the result page also shows the reasons for the first rows.
- **AutoML screens** for experts (the detailed view): column statistics and charts,
  correlations, leak warnings, every training setting, the job list, leaderboards, variable
  importance, score history, CV metrics, model export and import.
- **Model explanations**: diagnostics from the cross-validation predictions (confusion matrix,
  per-class metrics, ROC and precision-recall curves, calibration, residuals), importance from
  each column's contributions, partial dependence curves, and each prediction's contributions
  in the UI, the API, batch predictions and Fione Serving. Columns that predict the answer
  suspiciously well are flagged as possible leaks.
- **Its own AutoML engine**: gradient boosting with LightGBM, XGBoost and CatBoost, random
  forest and extremely randomized trees, a linear model, a neural network and, for data with text
  columns, a TF-IDF linear model (and, when time is left, variants of it), tuned with
  Optuna and ensembled, within the run time you set. It also builds derived features (text parts and
  topics, counts, sums, group means), keeping only those that clearly improve a quick test model, and
  averages extra seeds of the best models when time is left.
- **Fione Serving**: a small prediction API (`/invocations`, `/model`, `/ping`) for any trained
  model, as one shared Docker image and the model files.
- **Users and sharing**: administrators, editors and viewers; projects are shared per user.
  API tokens and a REST API (`/api/v1`) for scripts.
- **Python modules** for data operations (built-in frame operations, k-means, low-rank
  factorization; administrators can upload their own).
- **Python client** `fione-sdk` for scripts and notebooks of your own.
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

## Python client

A script or your own Jupyter can drive Fione with `fione-sdk` (`sdk/`, `pip install ./sdk`):
datasets, data profiles, AutoML training, leaderboards, predictions and Python modules, as
pandas frames, with an API token. See [sdk/README.md](sdk/README.md).

## MCP and the assistant

MCP clients such as Claude Code or Codex can read your projects at `/mcp` with an API token
(`FIONE_MCP_ENABLED=true`, off by default), and a second switch lets them also create projects,
upload datasets, queue training, prediction and module jobs, follow them and predict rows. See
[MCP](docs/mcp.md).

The assistant is an optional chat in the browser, off by default: it answers questions about a
project's datasets and models, comments on pages, and suggests a training run that a person
confirms; it only reads. It needs a language model (`FIONE_LLM_PROVIDER`): the Ollama app on your
Mac (`gemma4:12b-mlx`), an Ollama in Compose (profile `ollama`) on Linux, or Claude through the
Anthropic API (`claude` and an API key). A server outside this machine needs an administrator's
one-time consent. See [The assistant](docs/assistant.md).

## Documentation

- [Quick start](docs/quickstart.md)
- [MCP](docs/mcp.md): using Fione from AI tools, the tools that start jobs
- [The assistant](docs/assistant.md): the optional chat, its language model, what is sent,
  proposals
- [Configuration](docs/configuration.md): every setting, reverse proxy, backups of the secret key
- [Fione Serving](docs/serving.md): running a model as a prediction API
- [Known limitations](docs/known-limitations.md)

## Status

This release covers the core: data, analysis, AutoML, models and their explanations,
predictions, serving, jobs, users and sharing, a Python SDK, an MCP server and an optional LLM
assistant.
**Planned, not in this release**: ONNX export. No images are published yet;
you build them from the repository (a version tag publishes the `fione` and `fione-serving`
images).

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

## Help and support

- Questions: the [Fione forum](https://discuss.codelibs.org/c/fioneen/) (Japanese:
  [discuss.codelibs.org/c/fioneja](https://discuss.codelibs.org/c/fioneja/)).
- Bugs and suggestions: [GitHub issues](https://github.com/codelibs/fione/issues). Pull requests
  are welcome.
- Commercial services for Fione are offered by CodeLibs, Inc., the developer of Fione: see
  [codelibs.co](https://codelibs.co/product/fione.html).

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

The Compose stack also runs SeaweedFS (Apache-2.0) and, with the `ollama` profile, Ollama (MIT).
