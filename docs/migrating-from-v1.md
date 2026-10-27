# Moving from Fione v1 to v2

Fione v2 keeps v1's idea (a CSV in the browser, a model, a prediction API) and its main path
(upload → data analysis → run → prediction summary → predict / serve), but it is a new
implementation. Japanese: [v1 から v2 への移行](migrating-from-v1.ja.md).

## What changed

| | v1 | v2 |
|---|---|---|
| Runs as | A plugin of Fess (Java, LastaFlute) | Its own server (Python, FastAPI), no Fess or Elasticsearch |
| AutoML engine | H2O | Fione's own: LightGBM, XGBoost, CatBoost and scikit-learn's ExtraTrees, tuned with Optuna and ensembled |
| Storage | MinIO (JSON and files) | SeaweedFS or any S3-compatible storage for data and models; SQLite for users, projects, jobs and model records |
| Start | Fess and H2O set up separately | `docker compose up` (Fione and SeaweedFS) |
| Users and roles | Fess users with the roles `admin-easyml`, `admin-automl` and `admin-systemml`, which also decided the screens | Fione's own users with one role each: **admin**, **editor** or **viewer**; each project has an owner and can be shared with others as editor or viewer. The simple or detailed view is a display preference, not a permission. |
| Serving | A zip with a Dockerfile, `fione-serving.jar` and an H2O MOJO; you ran `docker build` | The model files and one shared `fione-serving` image; you run `docker run` ([Fione Serving](serving.md)) |
| Python modules | Scripts for the H2O Python API | A small new API: a function that takes and returns pandas DataFrames ([below](#python-modules)) |
| Automation | None besides serving | A REST API under `/api/v1` with API tokens (OpenAPI at `/api/docs`) |

## What is not carried over

- **H2O models cannot be migrated.** They are H2O binaries; train again in v2.
- **v1 data is not read.** v2 does not read v1's MinIO bucket. Upload your CSV files again and
  retrain.
- **Users are not migrated.** Create them again (an administrator does so on the Users page).
- **Python modules need a rewrite** for the new API.
- **H2O Flow, Rapids and MOJO/genmodel downloads are gone.** Notebooks (JupyterLab with
  a Python SDK, see [Notebooks](notebook.md)) are Flow's successor; data operations are
  pandas-based modules.

## Terms

The Japanese screen terms are kept.

| English (v2 UI) | 日本語 |
|---|---|
| Project | プロジェクト |
| Data analysis | データ分析 |
| Column to predict ("What do you want to predict?") | 予測する列 |
| Input columns | 入力する列 |
| Maximum run time | 最大実行時間 |
| Run | 実行 |
| Prediction summary | 予測結果サマリー |
| Fione-kun | Fione 君 |
| Datasets: Training data / Data to predict / Predictions | 学習データ / 予測するデータ / 予測結果 |
| Job | ジョブ |

## Feature by feature

| v1 feature | v2 |
|---|---|
| Create and delete projects | Shipped |
| Datasets (training, test, prediction), CSV upload and download | Shipped |
| Frame parsing, type changes, export, save | Partly: CSV parsing with type inference (stored as Parquet), CSV download, and Python modules that save their result as a new dataset. Changing a column's type by hand is not available yet |
| Column view, data view, per-column EDA | Shipped, extended: missing values, correlations, outliers, leak suspects, inferred types |
| EasyML wizard and AutoML screens | Shipped (the simple and detailed views) |
| AutoML run with its parameters (folds, class balancing, seed, maximum models and run time, per-model time, stopping rounds/metric/tolerance, sort metric, keeping CV predictions/models/fold assignment, excluded columns) | Shipped |
| Job list, delete, delete all, cancel | Shipped |
| Leaderboard and model details (importance, score history, CV metrics) | Shipped |
| Model explanations | New: diagnostics (confusion matrix, ROC and precision-recall curves, calibration, residuals), each column's contribution to a prediction, importance from those contributions, and partial dependence curves. Contributions come from the libraries' own tree explanations and are approximate for the ensemble ([Known limitations](known-limitations.md#explanations-and-leak-warnings)) |
| Model export, import, export of all models | Shipped (import is for administrators) |
| Batch prediction saved as a prediction dataset | Shipped |
| Prediction summary (best model, star rating, Fione-kun) | Shipped |
| Serving zip | Replaced by the serving bundle and the shared image |
| MOJO / genmodel download | Removed. ONNX export is planned where possible |
| H2O Flow | Removed. Replaced by [Notebooks](notebook.md): JupyterLab in a container per user, with the Python `fione-sdk` (opt-in) |
| Rapids | Removed (pandas-based modules) |
| Python modules: frame operations (cbind, concat, cor, cslice, fillna, floor, pivot, rbind, replace, rslice, sort, split, tokenize) | Shipped as built-in modules |
| Python modules: kmeans training and prediction | Shipped (scikit-learn KMeans) |
| Python modules: glrm training and prediction | Replaced by `lowrank_train` / `lowrank_predict` (scikit-learn TruncatedSVD / NMF) |
| Python modules: word2vec | Not shipped; a text-embedding module is planned |
| Module upload and reload | Shipped, administrators only, with a warning (modules are not sandboxed) |
| systemml screen (H2O status, cluster shutdown) | Replaced by the **System status** page (jobs, storage, workers) |
| Three roles and per-user sessions | Rebuilt: admin / editor / viewer and project sharing |
| English and Japanese | Shipped |

Planned, **not in this release**: the LLM assistant (Ollama, by default with `gemma4:12b-mlx`
on a Mac), an MCP server and ONNX export.

## Python modules

A v2 module is one Python file with a `MODULE` description and a `run` function. A frame
module, for example:

```python
MODULE = {"name": "Add one", "kind": "frame", "params": {"type": "object", "properties": {}}}


def run(df, params, ctx):
    return df + 1
```

The built-in frame modules keep v1's names and parameters, with three differences: `sort`
sorts ascending by default (v1: descending), `split` returns its parts in the order train,
valid, test (v1: train, test, valid), and in row conditions `&` means AND and binds tighter
than `|` (v1 treated `&` as OR).

`run` receives a pandas DataFrame and the parameters (checked against the JSON schema in
`params`) and returns a DataFrame. Administrators upload modules on the **Python modules**
page or with `POST /api/v1/modules`; jobs run them with
`POST /api/v1/projects/{id}/jobs/module`. Uploaded modules run in the job worker with the
server's privileges, without a sandbox: upload only code you trust.

## REST API

v1 had no public API besides serving. v2's API is under `/api/v1`; its OpenAPI document is
at `/api/docs`. Scripts authenticate with an API token from the
**Account** page: `Authorization: Bearer <token>`. A token acts as its user, with that user's
role and projects.
