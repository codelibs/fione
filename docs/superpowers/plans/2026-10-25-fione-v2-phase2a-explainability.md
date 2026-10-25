# Fione v2 Phase 2a (Explainability) Implementation Plan

> Work through the plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain Fione's models: per-row contributions, global importance from contributions, partial dependence / ICE, and training-time diagnostics (confusion matrix, per-class metrics, ROC/PR, calibration, residuals). Contributions are available through the API, batch prediction, Fione Serving and the UI. A cheap out-of-fold leak score warns about columns that predict the target suspiciously well.

**Architecture:**
- **Engine.** `fione.engine.explain` computes contributions natively per model family. It converts them into the ensemble's output space, combines them over the Caruana members, and maps them back to the input columns through `prep.sources`. It also holds partial dependence. `fione.engine.diagnostics` turns the blended OOF predictions into a small JSON at training time. That JSON is stored on `TrainedModel` and in a new `models.diagnostics_json` column, never as an artifact file.
- **Jobs and requests.** A short `explain` job precomputes global importance and the top-10 PD/ICE into `model_explanations`. The web process loads models only for small synchronous requests: at most 100 rows of contributions, or one PD column. Those requests go through one semaphore and a small LRU of loaded models (`fione.models.live`).

**Tech Stack:**
- Existing stack: Python 3.12, FastAPI, Jinja2, HTMX, ECharts, SQLite, pandas, pyarrow, LightGBM, XGBoost, CatBoost, scikit-learn, pytest, Playwright.
- No new packages. `scipy` is already installed through scikit-learn; it becomes an explicit dependency (Task 1).

**Spec:** `docs/superpowers/specs/2026-10-24-fione-v2-design.md` (sections 5, 6, 8, 9; this plan is the "SHAP / partial dependence / leak detection" part of Phase 2 in section 10). Phase 1 conventions: `docs/superpowers/plans/2026-10-24-fione-v2-phase1.md`.

## Global Constraints

Each decision below gives its reason after the dash.

- **No `shap` dependency.** Contributions use the libraries' native TreeSHAP:
  - LightGBM `pred_contrib`;
  - XGBoost `pred_contribs` with `iteration_range=(0, spec.rounds(model))`;
  - CatBoost `ShapValues`.

  ExtraTrees uses Saabas path contributions. — For the boosters, shap computes the same TreeSHAP as the native routes. Its exact ExtraTrees algorithm takes about 10 min per 1,000 rows.
- **Combining the contributions across the ensemble:**
  - Regression: the weighted sum of the members' contributions. This is exact.
  - Binary classification: rescale each booster's margin contributions to probability space with `(p(x) − p(bias)) / (margin(x) − bias)`. It is exact and keeps the signs.
  - Multiclass: integrate the softmax gradient along the path from the bias to the margin (16-point midpoint rule), then fold the residual in so the sums are exact (Task 1).

  The order is fixed: convert each fold model to probability space, average the member's fold models, then weight the members. — The ensemble averages probabilities, so converting must come before averaging.

  All three are additive in probability space or target units. Exact Shapley values exist only per booster in margin space. The docs call the explanations "approximate" (Task 13).
- **What each output explains, everywhere:**

  | Model | Output explained | Bias name |
  |---|---|---|
  | Binary | the positive class `classes_[1]` | — |
  | Multiclass | the predicted class, unless a `class_index` is given | — |
  | Regression | the value | — |
  | Any | — | "average prediction" (UI) / `bias` (API) |

  The contributions are keyed by the model's input columns (`TrainedModel.columns`). Dropped constant and all-null columns do not appear.
- **No artifact sidecar files.** The diagnostics live in `TrainedModel.diagnostics` (class default `None`, so Phase 1 pickles load) and in `models.diagnostics_json`. — The serving loader hashes every file in the manifest, and the serving bundle and model import refuse extra files.
- **PD/ICE is our own code**, not sklearn's `partial_dependence`:
  - n ≤ 300 background rows, grid ≤ 20 points, ICE ≤ 50 rows;
  - integer columns are supported.

  — sklearn refuses integer columns and was 9x slower in the measurement.
- **Synchronous work in the web process is limited** to contributions for ≤ 100 rows and PD for one column. It goes through `LiveModels`:
  - one `BoundedSemaphore(1)`; a request that cannot take it within 15 s gets 503 / a "busy" message;
  - an LRU of ≤ 2 loaded models and ≤ 512 MiB of artifact bytes.

  Everything else runs in jobs. — Contributions cost 30-300x a prediction, and the libraries use every core.
- **The web process loads only trusted models.** Phase 1 never unpickled a model in the web process. Now a viewer's request can make it load one. `LiveModels` therefore refuses records with `trusted=0` (foreign imports accepted on an admin's word): the API answers 409 `untrusted`, and the UI shows `explain.untrusted`. Such models are explained only by the explain job, which needs write access. — Loading a pickle runs code, and the known-limitations page already warns about these files.
- **Leak scores warn, they never deselect.** Score-based reasons never remove a column from the EasyML default inputs:
  - Pearson ≥ 0.99 ("near-perfect correlation with target");
  - the new "predicts the target on its own";
  - the new "row order follows the target".

  Only the exact reasons keep deselecting: "identical to target" and "value determines target". — On clean data the best legitimate column (iris petal width, 0.968) scores within 0.003 of a noisy copy of the target (0.971), so no threshold separates them.
- **Serving: contributions are opt-in** with `"contributions": true`:
  - the request has its own instance cap and in-flight cap;
  - the default `/invocations` response and `/model` stay byte-identical to Phase 1 (no new `/model` key).

  — Spec 8 fixes the contract, and Phase 1 pins it with contract tests.
- **Data-derived values in LLM tools** follow the Phase 1 privacy matrix (`tools/builtin.py` docstring). Without `allow_samples`, the following are removed:
  - class labels;
  - categorical PD grid levels;
  - regression actual-vs-predicted points.

  Names always pass through `clean_text`.
- **Every new route follows Phase 1:**
  - an id is resolved, then authorized on its own project (404 without read access);
  - writes need write access (403 for a viewer);
  - web POSTs check CSRF and Origin through `web.access.action`;
  - API POSTs use bearer, or cookie plus `X-CSRF-Token`;
  - Jinja autoescape is on, and chart data goes in `|tojson` JSON blocks;
  - the strict CSP holds: no inline script or style attributes, so colour comes from CSS classes;
  - error text shown to non-admins goes through `redact`.
- **Required with every change:**
  - en and ja i18n parity (`tests/unit/test_i18n.py`);
  - every new route gets rows in `tests/api/test_permissions.py` or `tests/web/test_routes.py` (route × persona);
  - every new `FIONE_*` name goes in `docs/configuration.md` (`tests/unit/test_docs.py`).
- **Version and licences.** The version stays `20.0.0`. Licences: Apache-2.0, MIT, BSD, ISC, PSF and 0BSD only. `scipy` (BSD-3) is already installed through scikit-learn. Task 1 imports `scipy.sparse` directly, so it adds `scipy>=1.18.1` to `pyproject.toml` dependencies. `uv lock` must change no installed version, and `uv run python scripts/check_licenses.py` must still exit 0.
- **DB migrations** are appended to `db.MIGRATIONS`, never edited (Tasks 3 and 7).
- **Commits.** Messages are public-safe implementation summaries with no attribution lines, written to a file and committed with `git commit -F <file>`. Work on branch `v2-phase2a`. Tracked files hold no local paths or user names.
- **Machine load:**
  - Run the tests you change, plus `uv run pytest -q -x`, once per task.
  - Run `-m timing` and `-m acceptance` only where a task says so, on an idle machine (1-minute load average below 4).
  - The e2e tests (`-m e2e`) need Docker. Where Docker is unavailable, record them as not run, never as passed.

## Review Focus

1. **Models without the new data.** These are:
   - Phase 1 models and imported models (diagnostics `None`, no explanation);
   - old exports, which have no `diagnostics` field;
   - models whose training dataset was deleted.

   Pages show a note, APIs return `null` or a clear status, and the explain job fails with a readable message. Never a 500. Tests: Tasks 3, 7, 11, 12.
2. **Awkward rows still explain additively.** NaN, unseen categories, datetime strings, a row equal to the bias, an empty frame: Σ contributions + bias = prediction. Tests: Task 1.
3. **Degenerate classes.** A fold model that never saw a class, a class never predicted (precision undefined), more than 30 classes, a bool target. The output is JSON-safe (`allow_nan=False`), with zeros embedded and caps applied. Tests: Tasks 1, 2.
4. **Hostile or colliding names.** Japanese, `<script>`, `contrib_x`, `contrib_bias`, `bias`, `BiasTerm`, and the label `"1"` next to `1`:
   - they are escaped in HTML and JSON;
   - batch output renames an input column that collides;
   - in serving responses the bias sits outside the column map.

   Tests: Tasks 1, 9, 10, 11, 12.
5. **Concurrent explanation requests.**
   - A second synchronous request while one is running gets a fast 503 or a "busy" fragment, never a hang.
   - A flood of serving contribution requests gets 503s, while plain predictions keep working.

   Tests: Tasks 8, 10, 12.

**Careful review required:**
- Task 1: contribution maths.
- Task 5: the leak flag rule.
- Task 10: the serving contract.

The other tasks get the standard review.

---

## File Structure

```
src/fione/engine/explain.py        # contributions, PD/ICE, global importance (Tasks 1, 4)
src/fione/engine/diagnostics.py    # OOF diagnostics JSON (Task 2)
src/fione/engine/model.py          # TrainedModel.diagnostics (Task 2)
src/fione/engine/prep.py           # Prep.kind_of (Task 4)
src/fione/data/profile.py          # leak check v2 (Task 5)
src/fione/models/service.py        # ModelRecord.diagnostics, submit_batch_predict flag (Tasks 3, 9)
src/fione/models/transfer.py       # optional diagnostics in record.json (Task 3)
src/fione/models/explanations.py   # model_explanations rows, submit_explain (Task 7)
src/fione/models/live.py           # LiveModels: semaphore + LRU (Task 8)
src/fione/projects/ingest.py       # read_dataset_spread (Task 7)
src/fione/jobs/explain_handler.py  # the explain job (Task 7)
src/fione/predict/batch.py         # contribution columns (Task 9)
src/fione/api/routes_explain.py    # diagnostics, explanations, contributions, PD (Task 8)
src/fione_serving/app.py           # opt-in contributions (Task 10)
src/fione/web/{easyml,automl,models_ui}.py, templates/{model,result,analysis,dataset,column,_pd,_why}.html,
  static/js/charts.js, static/css/app.css        # Tasks 6, 9, 11, 12
src/fione/tools/builtin.py         # leak reasons, new tools (Tasks 6, 13)
tests/unit/test_engine_explain.py, test_engine_diagnostics.py, test_handler_explain.py,
tests/api/test_explain_api.py, tests/acceptance/test_explain_adult.py
```

---

### Task 0: Check CatBoost's tree count on Adult (investigation, time-boxed)

One measurement under load gave the engine's CatBoost fold models only 6 trees on Adult with a 120 s budget. Find out whether that is an engine problem or an artefact of the load.

**Files:**
- Nothing is committed by default.
- Engine defect: a failing test in `tests/unit/test_engine_search.py` and the fix it points to.
- Load artefact: one line in `docs/known-limitations.md`, English and Japanese summary.

**Interfaces:**
- Consumes: `AutoML`, `TrainConfig(keep_cv_models=True)`, and the Adult loader in `tests/acceptance/test_engine_targets.py`.
- Produces: a short report to the lead with the numbers.

- [ ] **Step 1:** Check that the machine is idle: `sysctl -n vm.loadavg` (macOS) or `cat /proc/loadavg`.
  - Go on only when the 1-minute value is below 4. Wait up to 30 min.
  - If the machine is still busy, report "blocked: machine busy" and continue with Task 1. Task 1 does not depend on this result.
- [ ] **Step 2:** Run a throwaway script that is never committed and lives outside the repository. It trains Adult on the acceptance test's split with `max_runtime_secs=120` and `keep_cv_models=True`, collecting the events. Record:
  - the load average before and after;
  - CatBoost's trial count, and each trial's state and elapsed time;
  - `[m.tree_count_ for m in model.cv_models["CatBoost"]]` and `m.get_best_iteration()`;
  - the tail of the validation loss from `m.get_evals_result()`;
  - CatBoost's search share: the time between its first and last trial events.
- [ ] **Step 3: Decide.**
  - **Engine problem:** the idle fold models have fewer than 50 trees and their validation loss was still falling over the last 10 iterations (the deadline stopped them, not early stopping).
  - **Load artefact:** the idle run has ≥ 50 trees, or early stopping chose the few trees. Add to known-limitations: "On a heavily loaded machine the time budget buys fewer boosting rounds; CatBoost is affected most." Commit.
  - **Engine problem:** stop and send the lead the numbers and a proposed fix before writing code. The fix becomes its own reviewed change.
  - Time box: two training runs and 30 minutes.
- [ ] **Review Focus:** are the numbers from an idle machine? Does the decision follow the rule?

### Task 1: Engine contributions (`engine/explain.py`) — careful review

**Files:**
- Create: `src/fione/engine/explain.py`, `tests/unit/test_engine_explain.py`.
- Modify: `pyproject.toml` (explicit `scipy`), `uv.lock`.

**Interfaces:**
- Consumes:
  - `TrainedModel.members`, `.prep`, `.columns`, `.classes_`, `.task`;
  - `FamilySpec.view`, `.rounds(model)`, `.n_classes`;
  - `families.n_threads(n_rows)`.
- Produces:
  - `Contributions` (frozen dataclass):
    - `columns: list[str]`: equal to `model.columns`;
    - `outputs: list`: `[classes_[1]]` (binary), `classes_` (multiclass) or `[target]` (regression);
    - `values: np.ndarray`: shape (n, len(outputs), len(columns)), float64;
    - `bias: np.ndarray`: shape (n, len(outputs));
    - `prediction: np.ndarray`: shape (n, len(outputs)), equal to `values.sum(-1) + bias`;
    - `slots(class_index: int | None = None) -> np.ndarray`: the output index explained per row, shape (n,) — 0 for binary and regression; for multiclass `prediction.argmax(1)`, or `class_index`, which must lie in `range(len(outputs))` (`ValueError` otherwise).
  - `contributions(model: TrainedModel, df: pd.DataFrame) -> Contributions`. `ConfigError` for missing columns, as `predict` does.
  - Pure helpers, tested alone:
    - `binary_to_probability(phi: (n,f), bias: (n,)) -> (phi_p, bias_p)`;
    - `softmax_to_probability(phi: (n,k,f), bias: (n,k), steps: int = 16) -> (phi_p, bias_p)`;
    - `saabas(estimator, X: np.ndarray, n_outputs: int) -> (phi: (n,k,f), bias: (n,k))` for one sklearn tree.
  - `native_contributions(spec: FamilySpec, model, view: pd.DataFrame) -> (phi, bias)`, in the family's own space. Boosters give margins; ExtraTrees and regression give probabilities or values. Shapes are (n, k_m, f) and (n, k_m), with k_m = 1 for binary and regression.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_engine_explain.py`. Models come from a session-cached fixture of only three fits, which keeps the load low: one four-family `AutoML(TrainConfig(target, max_runtime_secs=15, max_models=4, nfolds=3, keep_cv_models=True))` per task on `tests/unit/predict_models.training_frame`. The targets are a binary target (`判定 == "良"`), the 3-class `判定` and `value`. Build the single-family models and the mixed members from each fit's `cv_models` and `prep` with `dataclasses.replace`.
  - `test_binary_rescale_is_additive_and_keeps_signs`: random φ and bias. `sigmoid(bias + φ.sum(1)) == phi_p.sum(1) + bias_p` (atol 1e-12), and `sign(phi_p) == sign(phi)`.
  - `test_binary_rescale_when_margin_equals_bias`: Σφ = 0 with nonzero entries. The result is finite, `phi_p == phi * σ'(bias)`, and the sums are exact.
  - `test_softmax_path_integral_is_additive`: `phi_p.sum(-1) + bias_p == softmax(bias + φ.sum(-1))` (atol 1e-9), and `bias_p == softmax(bias)`.
  - `test_feature_raising_only_class_c_never_lowers_p_c`: φ[:, c, i] > 0 and φ[:, j≠c, i] = 0, so `phi_p[:, c, i] >= 0`.
  - `test_all_zero_contributions_spread_the_residual_evenly`: φ = 0, so the output is finite and the sums are exact.
  - `test_saabas_matches_the_tree`: one fitted `ExtraTreeClassifier`/`ExtraTreeRegressor`. `phi.sum(-1) + bias == predict_proba` / `predict` (atol 1e-12).
  - `test_family_contributions_are_additive[family × task]`: 4 families × {binary, multiclass, regression}, single-family models.
    - Classification: `c.prediction == model.predict_proba(X)[outputs]`.
    - Regression: `c.prediction[:, 0] == model.predict(X)`.
    - `assert_allclose(rtol=1e-5, atol=1e-5)`.
  - `test_mixed_ensemble_refit_like_and_fold_fallback`: four-family members from `cv_models`, weights 0.4/0.3/0.2/0.1.
    - Refit-like: the first fold model of each family.
    - Fold fallback: all fold models.
    - Both are additive against `predict_proba`, binary and multiclass.
  - `test_xgboost_early_stopped_fold_model`: a fold model with `best_iteration + 1 < num_boosted_rounds()` is still additive.
  - `test_fold_model_missing_a_class`: an ExtraTrees fold model fitted without class 2 (`n_classes=3`) and put into a member. It is additive against `spec.predict`'s zero-filled output, and class 2's contributions are 0.
  - `test_datetime_parts_sum_into_their_column`: a frame with a datetime column. `c.columns == model.columns` (no `__year` names), and the result is additive.
  - `test_awkward_rows_are_additive`: NaN numbers, an unseen category, a missing category and datetime strings. All are additive.
  - `test_empty_frame`: shapes `(0, k_out, c)` and `(0, k_out)`, with no library call (spy).
  - `test_hostile_column_names_are_kept`: columns `"幅"`, `"<b>x</b>"`, `"BiasTerm"` and `"contrib_x"` appear unchanged in `c.columns`.
  - `test_slots`: binary gives zeros; multiclass gives the argmax, or `class_index`; an out-of-range `class_index` gives `ValueError`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_engine_explain.py -q`. Expected: FAIL (`ModuleNotFoundError: fione.engine.explain`).
- [ ] **Step 3: Implement `native_contributions`**:
  - **LightGBM:** `model.predict(view, pred_contrib=True, num_iteration=spec.rounds(model))`. Multiclass returns (n, k·(f+1)), class-major, so reshape it to (n, k, f+1). The bias is the last entry.
  - **XGBoost:** `model.get_booster().predict(xgb.DMatrix(view, enable_categorical=True), pred_contribs=True, iteration_range=(0, spec.rounds(model)))`.
  - **CatBoost:** `model.get_feature_importance(Pool(view, cat_features=[i for i, d in enumerate(view.dtypes) if d is np.dtype(object)]), type="ShapValues", thread_count=n_threads(len(view)))`.
  - **ExtraTrees:** the mean of `saabas` over `model.estimators_`, on `view.to_numpy(np.float32)`.
  - **A classifier that lacks classes** (`len(model.classes_) < spec.n_classes`): convert in the model's own class set, then embed it into the k slots. Absent classes get 0 contribution and 0 bias.

  **Saabas for one tree:**
  - Take the node values (classifier: `tree_.value[:, 0, :]`, each row normalised to sum 1; regressor: `tree_.value[:, 0, :1]`).
  - Build the parent of each node from `children_left`/`children_right`.
  - `delta[node] = value[node] − value[parent]`, credited to `feature[parent]`. Put it in a `scipy.sparse.csr_matrix` with shape (n_nodes, f·k).
  - `phi = estimator.decision_path(X) @ delta` reshaped to (n, f, k), then transposed to (n, k, f). `bias = value[0]` for every row.
- [ ] **Step 4: Implement the conversions and `contributions`.**
  - Binary rescale: `phi_p = phi · (σ(m) − σ(b)) / (m − b)` with `m = b + Σφ`. Where `|m − b| < 1e-9`, use `phi_p = phi · σ(b)(1 − σ(b))`. `bias_p = σ(b)`.
  - Multiclass: the algorithm below, which the tests do not determine on their own.

    ```text
    z0 = bias (n,k); d = phi.sum(-1) (n,k); t_s = (s + 0.5)/steps, s = 0..steps-1
    phi_p = mean_s [ p(t_s)[:,:,None] * (phi - (p(t_s)[:,:,None] * phi).sum(1, keepdims)) ],  p(t) = softmax(z0 + t·d)
    bias_p = softmax(z0)
    r = softmax(z0 + d) - bias_p - phi_p.sum(-1)                  # residual per (row, class)
    w = |phi_p|; W = w.sum(-1)
    phi_p += where(W > 0, r * w / W, r / f)                      # fold the residual in, exact sums
    ```

  - `contributions`:
    - Build each member's view once.
    - Per fold model: native values, then probability space. Classification boosters use `binary_to_probability` for k = 2 or `softmax_to_probability`. ExtraTrees and regression stay unconverted.
    - Average over the member's models, then weight-sum over the members.
    - Binary: keep only the positive class, slot 1 of the probability pair. The negative class is its mirror image.
    - Group-sum the features into `model.columns` with `np.add.at`, through `prep.sources`.
    - `prediction = values.sum(-1) + bias`.
  - Add `scipy>=1.18.1` to `pyproject.toml` and run `uv lock`. Expected: `git diff uv.lock` changes only the `fione` package's dependency list.
- [ ] **Step 5:** `uv run pytest tests/unit/test_engine_explain.py -q && uv run ruff check . && uv run python scripts/check_licenses.py`. Expected: all pass, licence check exit 0.
- [ ] **Step 6: Commit** "Engine: additive per-column contributions for every model family".
- [ ] **Review Focus:**
  - Probability conversion comes before fold averaging.
  - XGBoost `iteration_range`.
  - The LightGBM multiclass reshape order.
  - The Saabas normalisation.
  - Residual fold-in signs.
  - Embedding for missing classes.
  - No library call on empty input.

### Task 2: Training-time diagnostics (`engine/diagnostics.py`)

**Files:**
- Create: `src/fione/engine/diagnostics.py`, `tests/unit/test_engine_diagnostics.py`.
- Modify: `src/fione/engine/model.py` (field), `src/fione/engine/automl.py`. The blend is at `automl.py:189` and `TrainedModel(...)` at `automl.py:196`.

**Interfaces:**
- Consumes: `y` (class codes 0..k-1, or floats), the `blended` OOF predictions (n, k) or (n,), and the `classes` list.
- Produces:
  - `diagnostics(task: Task, y: np.ndarray, pred: np.ndarray, labels: list | None, *, max_rows: int = 200_000, seed: int = 0) -> dict`;
  - `TrainedModel.diagnostics: dict | None = None`, the last field.
  - The dict is strict JSON: no NaN or inf, and floats rounded to 6 significant digits. Undefined values are `None`.

    ```text
    common:          {"version": 1, "task", "n_rows" (rows used), "sampled": bool}
    classification:  "labels": jsonable(classes), "confusion": {"classes": [index…, -1 = other], "matrix": [[int]]}
                     (rows actual, columns argmax; > 30 classes: the 30 largest by support + "other"),
                     "per_class": [{"class", "precision", "recall", "f1", "support"}] (≤ 200 by support,
                     "per_class_truncated": bool); binary only: "auc", "roc": {"fpr","tpr","threshold"},
                     "pr": {"precision","recall","threshold"} (≤ 200 points each, endpoints kept, thresholds
                     finite: inf -> 1.0), "calibration": [{"predicted","observed","count"}] (10 equal-width bins of
                     p(positive), empty bins omitted)
    regression:      "residuals": {"edges": [31], "counts": [30]} (residual = actual − predicted),
                     "by_decile": [{"predicted_mean","residual_mean","residual_std","count"}] (10 deciles of the
                     prediction), "points": {"actual": [...], "predicted": [...]} (≤ 2,000, seeded)
    ```

- [ ] **Step 1: Write the failing tests:**
  - `test_binary_matches_sklearn`:
    - the matrix equals `sklearn.metrics.confusion_matrix`;
    - P/R/F1 equal `precision_recall_fscore_support(zero_division=np.nan)`, with NaN mapped to `None`;
    - `auc == metrics.value("auc", …)`;
    - each curve has ≤ 200 points, and `threshold[0]` is finite.
  - `test_class_never_predicted_has_null_precision`: precision is `None`, and `json.dumps(d, allow_nan=False)` passes.
  - `test_bool_and_mixed_labels_are_json`: labels `[False, True]` and `["1", 1]` come back distinct and in order through `json.loads(json.dumps(d))`.
  - `test_many_classes_are_capped`: 100 classes on 20k rows. The matrix is 31×31, `classes[-1] == -1`, there are no curves, and `len(json.dumps(d)) <= 256 * 1024`.
  - `test_regression`:
    - the counts sum to `n_rows`;
    - there are 10 deciles;
    - there are ≤ 2,000 points;
    - an over-prediction gives a negative residual.
  - `test_sampling`: 250k rows give `n_rows == 200_000` and `sampled is True`. The same seed gives the same dict.
  - `test_automl_fit_stores_diagnostics`: iris, 10 s. `model.diagnostics["labels"] == jsonable(model.classes_)`.
  - `test_diagnostics_failure_does_not_fail_training`: patch `diagnostics` to raise. The fit returns `diagnostics is None` and emits a `notice` with `kind="diagnostics_error"`.
  - `test_phase1_pickle_loads_without_diagnostics`: `del model.__dict__["diagnostics"]`, then a `joblib` round trip. Expected: `.diagnostics is None`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_engine_diagnostics.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** with sklearn's `roc_curve(drop_intermediate=True)` and `precision_recall_curve`. Thin a curve to 200 points by taking evenly spaced indices that include both ends. In `AutoML.fit`:
  - call it right after `blended` is built;
  - catch any `Exception` there and emit the notice (`error_notice` style);
  - pass `diagnostics=` to `TrainedModel`.

  It runs in the reserve. Add a `@pytest.mark.timing` test: diagnostics on 200k binary rows take ≤ 1.0 s.
- [ ] **Step 4:** `uv run pytest tests/unit/test_engine_diagnostics.py tests/unit/test_engine_automl.py -q`. Expected: PASS.
- [ ] **Step 5: Commit** "Engine: confusion matrix, ROC/PR, calibration and residual diagnostics from the OOF predictions".
- [ ] **Review Focus:**
  - Strict JSON everywhere.
  - Rows are actual, columns predicted.
  - The positive class is `classes_[1]`.
  - The cost stays bounded at 200k rows.
  - A failure only produces a notice.

### Task 3: Persist diagnostics (record, migration, export/import)

**Files:**
- Modify:
  - `src/fione/db.py`: append a migration;
  - `src/fione/models/service.py`: `ModelRecord`, `_record` (`service.py:51`), `insert_model` (`:121`), `add_model` (`:88`); `list_models_brief` (`:184`) stays as it is;
  - `src/fione/models/transfer.py`: `RECORD_FIELDS` (`:61`), `_record_json` (`:112`), `_parse_record` (`:257`).
- Test: `tests/unit/test_models.py`, `tests/unit/test_model_transfer.py`, `tests/unit/test_db.py`.

**Interfaces:**
- Consumes: `TrainedModel.diagnostics` (Task 2).
- Produces:
  - migration `ALTER TABLE models ADD COLUMN diagnostics_json TEXT`;
  - `ModelRecord.diagnostics: dict | None = None`, the last field;
  - `insert_model(..., diagnostics: dict | None = None)`;
  - `transfer.OPTIONAL_RECORD_FIELDS = ("diagnostics",)`.

- [ ] **Step 1: Write the failing tests:**
  - `test_migration_keeps_existing_models`: a DB migrated to the previous version with one model row, then `migrate`. `get_model(...).diagnostics is None`.
  - `test_add_model_stores_diagnostics`.
  - `test_brief_records_have_no_diagnostics`.
  - `test_export_import_keeps_diagnostics`.
  - `test_import_of_export_without_diagnostics`: a Phase 1 `record.json` imports with `None`.
  - `test_import_rejects_bad_diagnostics`: the cases `[]`, `"x"`, `{"version": 2}` and a `task` that differs from the manifest. Each gives `ModelImportError` naming "diagnostics", and leaves no row and no objects.
- [ ] **Step 2:** `uv run pytest tests/unit/test_models.py tests/unit/test_model_transfer.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement:**
  - `_parse_record` accepts `set(RECORD_FIELDS) <= keys <= set(RECORD_FIELDS) | set(OPTIONAL_RECORD_FIELDS)`.
  - A `diagnostics` value must be a dict with `version == 1` and `task == manifest.task`.
  - `_record_json` writes `diagnostics` only when it is not `None`.
  - `insert_model` stores `_dumps(diagnostics)` or NULL.
- [ ] **Step 4:** Run the same tests plus `tests/unit/test_db.py`. Expected: PASS.
- [ ] **Step 5: Commit** "Store each model's diagnostics in its record and its export".
- [ ] **Review Focus:**
  - Phase 1 exports and rows still work.
  - A failed import leaves nothing behind.
  - Known limitation for Task 13: a Phase 1 install refuses an export that carries `diagnostics`, and the version does not tell the two apart during development.

### Task 4: Partial dependence / ICE and global importance

**Files:**
- Modify: `src/fione/engine/explain.py`, `src/fione/engine/prep.py`.
- Test: `tests/unit/test_engine_explain.py`.

**Interfaces:**
- Consumes: `Contributions` (Task 1), `TrainedModel.predict_proba/predict`.
- Produces:
  - `Prep.kind_of(column: str) -> Literal["numeric","datetime","category","frequency"]`. `KeyError` for a column the model does not use.
  - `PartialDependence` (frozen dataclass):
    - `column: str`;
    - `kind: Literal["numeric","datetime","category"]`, where frequency counts as category;
    - `grid: list`: JSON-able; `None` means missing; datetimes as ISO strings;
    - `outputs: list`: as `Contributions.outputs`;
    - `average: np.ndarray`: shape (G, len(outputs));
    - `ice: np.ndarray`: shape (n_ice, G), for `outputs[ice_output]`;
    - `ice_output: int`;
    - `n_rows: int`.
  - `partial_dependence(model, background: pd.DataFrame, column: str, *, grid_size: int = 20, max_rows: int = 300, ice_rows: int = 50, class_index: int | None = None, seed: int = 0) -> PartialDependence`.
    - Limits: `2 <= grid_size <= 20`, `1 <= max_rows <= 300`, `0 <= ice_rows <= 50`. Outside them it raises `ValueError`.
    - A column the model does not use, or one with no values in the background, raises `ValueError(f"... {column!r} ...")`.
  - `global_importance(c: Contributions) -> pd.Series`: the mean over rows of Σ over outputs of |values|, per column, sorted descending.
  - Constants: `PD_GRID = 20`, `PD_ROWS = 300`, `ICE_ROWS = 50`.

- [ ] **Step 1: Write the failing tests:**
  - `test_pd_matches_a_hand_computed_average`: regressor. A loop over the grid that sets the column and averages `predict` equals `average[:, 0]` (atol 1e-12).
  - `test_ice_rows_are_the_individual_curves`.
  - `test_sparse_numeric_column_gets_an_even_spread`: 95% zeros. ≥ 10 distinct grid points lie in [p2, p98].
  - `test_integer_column_gets_integer_grid`: an int64 column gives integral grid values and `kind == "numeric"`.
  - `test_categorical_grid_is_top_levels_plus_missing`: `grid_size=4` gives the 3 most frequent levels, then `None`.
  - `test_datetime_column_is_varied_on_the_raw_column`: the ISO strings are sorted and the average is finite.
  - `test_limits`:
    - `grid_size=21` gives `ValueError`;
    - `max_rows=301` gives `ValueError`;
    - `ice_rows=51` gives `ValueError`;
    - a dropped constant column gives `ValueError` naming it;
    - an all-NaN background column gives `ValueError`.
  - `test_background_is_sampled_with_the_seed`: 1,000 rows give `n_rows == 300`, the same result every time.
  - `test_multiclass_ice_defaults_to_the_most_varying_class`; `class_index` overrides it.
  - `test_global_importance_orders_by_mean_abs`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_engine_explain.py -q -k "pd or ice or grid or importance or limits"`. Expected: FAIL.
- [ ] **Step 3: Implement.** Repeat each background row G times, set the column to the tiled grid, and predict once. The grid rules are what the tests fix:
  - **numeric:** `unique(nanquantile(linspace(.02,.98,G)))`. When that gives fewer than G points, add `linspace(p2, p98, G)` and keep G evenly spaced indices of the sorted union, with both ends. Integral columns are rounded and made unique.
  - **category:** the top G−1 levels by count in the background (ties by label), then `None`.
  - **datetime:** quantiles of the timestamps' int64 values.

  Multiclass `ice_output = argmax(average.max(0) − average.min(0))`.
- [ ] **Step 4:** Run the whole test file. Expected: PASS.
- [ ] **Step 5: Commit** "Engine: partial dependence and ICE curves; importance from contributions".
- [ ] **Review Focus:**
  - The grid never exceeds 20 points.
  - Bool columns get the grid `[False, True, None]`.
  - One predict call per column.

### Task 5: Leak detection v2 (`data/profile.py`) — careful review

**Files:**
- Modify: `src/fione/data/profile.py` (`leak_suspects` `:243`, `profile_dataset` `:258`, `DatasetProfile` `:81`).
- Test: `tests/unit/test_profile.py`.

**Interfaces:**
- Consumes: `fione.engine.prep.infer_task`. `fione/engine/__init__.py` imports nothing, so this pulls in no model library.
- Produces:
  - constants `PREDICTS_ALONE = "predicts the target on its own"`, `ORDERED_BY_TARGET = "row order follows the target"`, `CORRELATED = "near-perfect correlation with target"`;
  - `SCORE_REASONS = frozenset({CORRELATED, PREDICTS_ALONE, ORDERED_BY_TARGET})`, `LEAK_STRONG = 0.99`;
  - `LeakCheck(suspects: list[LeakSuspect], partial: bool)`;
  - `leak_check(df, columns, target, *, time_budget: float = 3.0, max_rows: int = 10_000, min_rows: int = 200, clock: Callable[[], float] = time.monotonic) -> LeakCheck`;
  - `leak_suspects(...)` stays, and returns `leak_check(...).suspects`;
  - `single_column_score(s: pd.Series, kind: Kind, t: pd.Series, task: Task, *, seed: int = 0) -> float | None`;
  - `flag_scores(scores: dict[str, float], task: Task) -> set[str]`;
  - `DatasetProfile.leak_partial: bool = False`.
  - `LeakSuspect(column, reason, score)` keeps its shape.
  - Exact reasons win: a column flagged as identical or determines is not listed again.

- [ ] **Step 1: Write the failing tests.** They use synthetic data and bundled sklearn sets only (no network).
  - `test_flag_rule`:
    - `{"petal": .968, "sepal": .916}` gives none.
    - `{"copy": .971, "relationship": .777}` gives `{"copy"}`.
    - `{"a": .99, "b": .98, "c": .60}` gives `{"a", "b"}`.
    - Every column ≥ .95 with none below: compare with chance (0.5), so they are flagged.
    - Regression: `{"log": .984, "MedInc": .478}` gives `{"log"}`, and `{"x": .91, "y": .85}` gives none.
  - `test_injected_classification_leaks`: 5k rows of `make_classification(random_state=0)` with seven injected columns. Every one is flagged with a score-based reason, and the id and the timestamp get `ORDERED_BY_TARGET`. The columns are:
    - a copy of the target with 3% flipped;
    - the target code plus N(0, 0.1);
    - a perfect-threshold continuous column;
    - an int id sorted by the target;
    - a timestamp that increases with the target;
    - a 1,500-level code that is 98% pure;
    - an amount that is non-zero for 80% of positives.
  - `test_injected_regression_leaks`: `make_regression` shifted positive, with log(t) + noise, t² + noise, t rounded as a string, and a rank id. All are flagged.
  - `test_clean_datasets_raise_no_score_suspects`: `load_breast_cancer`, `load_digits`, `load_diabetes`. No suspect has a reason in `{PREDICTS_ALONE, ORDERED_BY_TARGET}`.
  - `test_few_rows_skip_the_score`: iris (150 rows) gives no score-based suspects.
  - `test_time_budget_sets_partial`: a fake clock that advances 2 s per call gives `partial is True` with some columns unscored, and `profile_dataset(...).leak_partial is True`.
  - `test_exact_reason_wins`: an identical column appears once, as "identical to target".
  - `test_high_cardinality_noise_scores_near_chance`: a random 5,000-level code scores ≤ 0.6.
- [ ] **Step 2:** `uv run pytest tests/unit/test_profile.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The algorithm below is the one decision the tests pin only in part.

  ```text
  rows: paired non-null (column, target); < min_rows -> skip scoring; > max_rows -> df.sample(max_rows, random_state=0)
  task = infer_task(target); binary target -> 0/1 (positive = second sorted label); multiclass -> codes
  bins: numeric/datetime/id-numeric -> searchsorted into unique quantile edges (64 bins); categorical/text/id-string ->
        factorize; NaN -> its own bin
  2 folds from a seeded permutation; for each fold: per-bin mean of the other fold's target (per class for multiclass),
        smoothed  (sum + 10 * global_mean) / (count + 10); a bin unseen in the other fold -> global_mean
  score: binary AUC; multiclass mean of per-class one-vs-rest AUCs; regression R^2 = 1 - SSE/SST (SST = 0 -> None)
  flag (flag_scores): threshold T = 0.95 (AUC) or 0.90 (R^2); baseline = max score < T, else 0.5 (AUC) / 0.0 (R^2);
        flagged when score >= T and score - baseline >= 0.10
  reason: ORDERED_BY_TARGET for kind "id" or "datetime", else PREDICTS_ALONE; score = the column's score
  columns scored in profile order, skipping the target, "constant" and exact-reason columns; stop when
        clock() - start > time_budget -> partial = True
  ```

  The current Pearson and exact checks stay as they are.
- [ ] **Step 4:** `uv run pytest tests/unit/test_profile.py -q`. Expected: PASS. Then `uv run pytest -q -m timing -k leak` on an idle machine: 21 columns × 10k rows ≤ 3 s.
- [ ] **Step 5: Commit** "Profile: an out-of-fold single-column score that flags likely target leaks".
- [ ] **Review Focus:**
  - The baseline is taken below the threshold.
  - No in-sample scoring.
  - Sampling is deterministic.
  - The time budget is respected.
  - The reason strings are exact (Task 6 maps them).

### Task 6: Surface the leak warnings (EasyML, dataset screens, tools)

**Files:**
- Modify:
  - `src/fione/web/easyml.py`: `LEAK_REASONS` (`:81`), `_analysis` (`:231-240`), `_warnings` (`:262`);
  - `src/fione/web/automl.py`: `_leaks` (`:133`);
  - `templates/{analysis,dataset,column}.html`;
  - `src/fione/tools/builtin.py`: `describe_dataset` (`:199`), `propose_training_config`, the tool descriptions;
  - `i18n/{en,ja}.json`.
- Test: `tests/web/test_easyml.py`, `tests/web/test_automl_ui.py`, `tests/unit/test_tools.py`.

**Interfaces:**
- Consumes: `SCORE_REASONS`, `LEAK_STRONG`, `DatasetProfile.leak_partial` (Task 5).
- Produces:
  - `LEAK_REASONS` gains `PREDICTS_ALONE -> "predicts_alone"` and `ORDERED_BY_TARGET -> "ordered"`.
  - `_analysis` column dicts gain `"warning": key | None` and `"score": float | None`. `reasons` keeps only the exact and kind reasons, which deselect.
  - `_leaks` returns `{column: {"key": str, "score": float, "exact": bool}}`.
  - Tools: each `leak_suspects` entry gains `"kind": "exact" | "score"`, and `describe_dataset` gains `"leak_check_partial": bool`.
  - New i18n keys (en and ja):
    - `analysis.reason.leak_predicts_alone`, `analysis.reason.leak_ordered`;
    - `analysis.warn.leak_scores`: "{n} columns predict the answer suspiciously well on their own. They stay checked: make sure each one is known at prediction time.";
    - `analysis.warn.leak_partial`, `dataset.badge.leak_score`, `column.leak_score`.
  - `analysis.warn.leaks` keeps "They are unchecked below", now counted over the exact suspects only.

- [ ] **Step 1: Write the failing tests:**
  - `test_score_suspect_stays_selected`: 300 rows with a noisy copy of the target. On the analysis page the column's checkbox is `checked`, its warning text is shown, and `analysis.warn.leak_scores` is a `warning` alert (score ≥ 0.99) or an `info` alert.
  - `test_exact_suspect_is_still_deselected`: an identical column is unchecked.
  - `test_iris_keeps_all_four_inputs_selected`.
  - `test_columns_tab_shows_the_score_badge`: the badge text and the score, to 2 decimals.
  - `test_describe_dataset_marks_score_reasons` (tools).
  - `test_proposal_does_not_suggest_ignoring_score_suspects`: the column is in `warnings`, with "check that it is known at prediction time", and absent from `ignored_suggestions`.
  - The existing sentinel-privacy tool tests still pass.
- [ ] **Step 2:** `uv run pytest tests/web/test_easyml.py tests/web/test_automl_ui.py tests/unit/test_tools.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the split in `_analysis`. Exact reasons go into `reasons`; reasons in `SCORE_REASONS` become the column's `warning`. Also:
  - grep `tests/web` for a test that expects a correlated column to be deselected; that behaviour is now warn-only, so update the test;
  - update the `describe_dataset` description: "…columns that may leak it (exact matches, and columns that predict it suspiciously well on their own)".
- [ ] **Step 4:** Run the tests above plus `tests/unit/test_i18n.py`. Expected: PASS.
- [ ] **Step 5: Commit** "Warn about columns that predict the target alone; deselect only exact leaks".
- [ ] **Review Focus:**
  - No score-based reason deselects.
  - The wording asks the user to check, never accuses.
  - Viewers see the warnings.
  - Tool output stays clean-texted.

### Task 7: The `explain` job and `model_explanations`

**Files:**
- Create: `src/fione/models/explanations.py`, `src/fione/jobs/explain_handler.py`, `tests/unit/test_handler_explain.py`.
- Modify:
  - `src/fione/db.py`: migration;
  - `src/fione/jobs/builtin.py`: import;
  - `src/fione/jobs/automl_handler.py`: auto-enqueue;
  - `src/fione/projects/ingest.py`;
  - `src/fione/config.py`;
  - `docs/configuration.md`;
  - `i18n/{en,ja}.json` (`job.kind.explain`);
  - `tests/api_helpers.py` and `tests/conftest.py`: default `explain_after_training=False`.

**Interfaces:**
- Consumes: `contributions`, `global_importance`, `partial_dependence` (Tasks 1, 4); `load_trained`.
- Produces:
  - Migration:

    ```sql
    CREATE TABLE model_explanations (model_id INTEGER PRIMARY KEY REFERENCES models(id) ON DELETE CASCADE,
      job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL, dataset_id INTEGER REFERENCES datasets(id)
      ON DELETE SET NULL, payload_json TEXT NOT NULL, created_at REAL NOT NULL)
    ```
  - `Explanation(model_id, job_id, dataset_id, payload: dict, created_at)`.
  - Service functions:
    - `save_explanation(conn, model_id, job_id, dataset_id, payload) -> None`, which replaces the row;
    - `get_explanation(conn, model_id) -> Explanation | None`;
    - `latest_explain_job(conn, model_id) -> Job | None`, by `json_extract(payload_json, '$.model_id')`;
    - `model_columns(record) -> list[str]`: the keys of `record.importance`, which equal `model.columns`, so nothing is unpickled;
    - `submit_explain(conn, user, project_id, model_id, dataset_id: int | None = None) -> Job`. It needs write access, a model and dataset of that project (`ModelNotFound`/`DatasetNotFound`), and a dataset with every model column (`ValueError("the dataset lacks the model's columns: [...]")`).
  - `ingest.read_dataset_spread(storage, dataset, rows: int, columns: list[str] | None = None, *, seed: int = 0, max_groups: int = 8) -> pd.DataFrame`. It reads at most `max_groups` evenly spaced row groups, then samples `rows` of their rows with `seed` (all of them if there are fewer), in file order. It is never biased towards the head.
  - Job kind `explain`, a short kind, with payload `{"model_id": int, "dataset_id": int | None}`.
  - `build_explanation(model, frame, should_stop) -> dict`:
    - importance from ≤ 1,000 rows, stratified by the target when the target is present and the model classifies;
    - PD for the top `min(10, n_columns)` columns by importance, on ≤ 300 rows.
    - Payload:

      ```text
      {"version": 1, "n_rows", "outputs", "importance": [{"column","mean_abs","share"}],
       "partial_dependence": [{"column","kind","grid","outputs","average","ice_output","ice","n_rows"}], "elapsed"}
      ```

      Multiclass `average` keeps at most 20 outputs: those with the highest mean predicted probability. The payload is strict JSON of ≤ 1 MiB.
  - `Settings.explain_after_training: bool = True` (`FIONE_EXPLAIN_AFTER_TRAINING`).
  - The automl result gains `explain_job_id`. It is `None` when explaining is disabled or enqueueing failed (logged, never raised).
  - The enqueue happens only after the handler's last `ctx.should_stop(force=True)` check has passed, the one that otherwise deletes the just-saved model. A cancel during the save therefore never leaves an explain job for a deleted model.

- [ ] **Step 1: Write the failing tests** (handler pattern of `tests/unit/test_handler_batch_predict.py`):
  - `test_explain_stores_importance_and_top_pd`: shares sum to 1 and are sorted. PD entries ≤ 10, in importance order.
  - `test_automl_enqueues_explain_when_enabled` and `..._not_when_disabled`.
  - `test_cancel_during_save_enqueues_no_explain_job`: no model row and no `explain` job.
  - `test_deleted_training_dataset_fails_clearly`: the job is FAILED with "the training data is no longer available; choose a dataset that has the model's columns".
  - `test_other_dataset_without_the_columns_is_refused`.
  - `test_dataset_of_another_project_is_refused`.
  - `test_rerun_replaces_the_explanation`.
  - `test_cancel_keeps_the_previous_explanation`.
  - `test_deleting_the_model_deletes_its_explanation`.
  - `test_read_dataset_spread_is_not_head_biased`: 200k rows sorted by the target, written as 4 row groups. The sample holds rows from every group and is the same each time.
- [ ] **Step 2:** `uv run pytest tests/unit/test_handler_explain.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement:**
  - The handler checks `should_stop()` between PD columns and emits a `notice` after each one.
  - `JobUserError` for user-fixable problems; `UntrustedArtifactError` becomes "the model file failed verification".
  - Add `FIONE_EXPLAIN_AFTER_TRAINING` to the "Fione settings" table.
  - grep `tests/` for job-count assertions after training and fix them. Explain jobs are listed like any other job, and `_active_jobs` filters by kind, so it is unaffected.
- [ ] **Step 4:** `uv run pytest tests/unit/test_handler_explain.py tests/unit/test_handler_automl.py tests/unit/test_docs.py tests/unit/test_i18n.py -q`. Expected: PASS.
- [ ] **Step 5: Commit** "Add the explain job: importance from contributions and the top partial dependence curves".
- [ ] **Review Focus:**
  - Imported models (`dataset_id` None) need an explicit dataset.
  - Cascade on delete.
  - The payload size cap.
  - A training job never fails because explaining failed to enqueue.

### Task 8: API routes and `LiveModels`

**Files:**
- Create: `src/fione/models/live.py`, `src/fione/api/routes_explain.py`, `tests/api/test_explain_api.py`.
- Modify:
  - `src/fione/api/app.py`: `ROUTERS`, and `app.state.live_models`;
  - `src/fione/api/routes_jobs.py`;
  - `src/fione/api/schemas.py`;
  - `tests/api/test_permissions.py`.

**Interfaces:**
- Consumes: Tasks 1, 3, 4, 7; `ingest.read_dataset_rows(storage, dataset, offset, limit, columns)`; `predict.batch._check_inputs` (make it public as `check_inputs`).
- Produces:
  - `LiveModels(storage, secret: bytes, *, max_models: int = 2, max_bytes: int = 512 << 20, wait_secs: float = 15.0)`.
    - `use(record: ModelRecord) -> ContextManager[TrainedModel]`. It raises `Untrusted` for a record with `trusted=0` before anything is read. Otherwise it takes the semaphore or raises `Busy`. The cache key is `(record.id, record.storage_prefix)` and the size is `storage.size(prefix + "model.joblib")`. A model above `max_bytes` is loaded but not kept.
    - `__len__`.
  - Schemas:
    - `ContributionsIn{instances: list[dict] | None (1..100), dataset_id: DbId | None, offset: int ≥ 0 = 0, limit: 1..100 = 10, class_index: int | None}`. Exactly one source: `instances`, or `dataset_id`.
    - `PartialDependenceIn{column: str (≤ 500), dataset_id: DbId | None, grid: 2..20 = 20, rows: 1..300 = 300, ice: 0..50 = 50, class_index: int | None}`.
    - `ExplainJobIn{model_id: DbId, dataset_id: DbId | None}`.
  - Routes under `/api/v1`. The model id is resolved on its own project, as `routes_models._model` does.

    | Route | Access | Response |
    |---|---|---|
    | `GET /models/{model_id}/diagnostics` | read | `{"model_id", "diagnostics": dict \| null}` |
    | `GET /models/{model_id}/explanations` | read | `{"model_id", "status": "none"\|"queued"\|"running"\|"done"\|"failed"\|"cancelled", "job_id", "dataset_id", "computed_at", "explanation": payload \| null}` |
    | `POST /models/{model_id}/contributions` | read | `{"model_id", "outputs", "rows": [{"row", "prediction", "class_index" (null unless multiclass), "bias", "contributions": {column: value}}]}` |
    | `POST /models/{model_id}/partial-dependence` | read | the `PartialDependence` fields |
    | `POST /projects/{project_id}/jobs/explain` | write | 201 `job_out` |

    - The PD background is the model's dataset, or `dataset_id`, through `read_dataset_spread(rows)`.
    - Errors:
      - `Busy` gives 503 `busy` with `Retry-After: 5`;
      - `Untrusted` gives 409 `untrusted`;
      - `PredictInputError` and `ValueError` give 422;
      - a dataset of another project, or a missing one, gives 404 "dataset not found";
      - a model with no dataset and no `dataset_id` gives 422 "choose a dataset".

- [ ] **Step 1: Write the failing tests:**
  - `test_diagnostics_null_for_a_phase1_model` (`store_model` with diagnostics `None`).
  - `test_contributions_for_instances_are_additive`: `bias + Σ contributions` equals what `/models/{id}` would predict for the instance.
  - `test_contributions_for_dataset_rows`.
  - `test_contributions_limits`: 101 instances, both sources, neither source, and a missing column each give 422.
  - `test_pd_one_column` and `test_pd_limits` (`grid=21` gives 422).
  - `test_viewer_may_explain_but_not_recompute`: 200 on contributions, 403 on `jobs/explain`.
  - `test_stranger_gets_404`.
  - `test_busy_is_a_fast_503`: hold the semaphore in the test with `wait_secs=0.1`. Expected: 503 in < 2 s, with `Retry-After`.
  - `test_live_models_lru_is_bounded`: 3 models give `len ≤ 2`, and an oversized model is not kept.
  - `test_cookie_post_needs_csrf`.
  - `test_untrusted_model_is_refused`: contributions and PD for a `trusted=0` model give 409 `untrusted`, nothing is unpickled (spy on `load_trained`), and `jobs/explain` for it still gives 201.
  - Rows in `tests/api/test_permissions.py` for all five routes:
    - the read routes expect the same codes as `GET /models/{model_id}`;
    - `POST /models/.../contributions` and `.../partial-dependence` expect the read codes, with 200 for viewers;
    - `jobs/explain` expects the codes of `POST /projects/{project_id}/jobs/batch-predict`.
- [ ] **Step 2:** `uv run pytest tests/api/test_explain_api.py tests/api/test_permissions.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The endpoints are sync `def`, so FastAPI runs them in its threadpool. `explanations` status:
  - `done` when a row exists and no newer explain job is queued or running;
  - otherwise the latest explain job's status, or `none`.
- [ ] **Step 4:** Run the tests above. Expected: PASS.
- [ ] **Step 5: Commit** "API: diagnostics, explanations, contributions and partial dependence of a model".
- [ ] **Review Focus:**
  - Ids are authorized on their own project.
  - Viewers get read-only access.
  - The semaphore is always released, on exceptions too.
  - The LRU is bounded by count and by bytes.
  - Errors pass through `service_errors` and `redact`.

### Task 9: Batch prediction `include_contributions`

**Files:**
- Modify:
  - `src/fione/predict/batch.py`: `included_columns` `:34`, `predict_chunks` `:116`, `_predict` `:139`;
  - `src/fione/jobs/batch_predict_handler.py`;
  - `src/fione/models/service.py`: `submit_batch_predict` `:281`;
  - `src/fione/api/schemas.py`: `BatchPredictIn`;
  - `src/fione/api/routes_jobs.py`;
  - the EasyML predict form: `web/easyml.py` `predict_run` and `templates/predict.html`;
  - i18n.
- Test: `tests/unit/test_batch_predict.py`, `tests/unit/test_handler_batch_predict.py`, `tests/web/test_easyml.py`.

**Interfaces:**
- Consumes: `contributions`, `Contributions.slots` (Task 1).
- Produces:
  - `contribution_columns(model) -> list[str]`: `[f"contrib_{c}" for c in model.columns] + ["contrib_bias"]`;
  - `included_columns(..., *, contributions: bool = False)`, whose reserved names include the contribution columns;
  - `predict_chunks(..., contributions: bool = False)`, whose output columns are: prediction columns, then contribution columns, then inputs;
  - constants `MAX_CONTRIBUTION_ROWS = 100_000`, `CONTRIBUTION_CHUNK_ROWS = 5_000`;
  - `submit_batch_predict(..., include_contributions: bool = False)`, which raises `PredictInputError("contributions are limited to 100,000 rows")` beyond the cap;
  - payload key `include_contributions`, where a missing key means `False`;
  - `BatchPredictIn.include_contributions: bool = False`;
  - form checkbox `contributions`, with i18n `predict.contributions` and `predict.contributions_hint` ("slower").

- [ ] **Step 1: Write the failing tests:**
  - `test_contributions_sum_to_the_prediction`:
    - binary: `Σ contrib_* == p_<classes_[1]>`;
    - multiclass: `Σ == p_<predicted>`;
    - regression: `Σ == predict`;
    - atol 1e-5.
  - `test_colliding_input_columns_are_renamed`: inputs `contrib_x` and `contrib_bias` become `input_contrib_x` and `input_contrib_bias`, and an input named `bias` stays `bias`.
  - `test_more_than_100k_rows_is_refused_at_submit`.
  - `test_payload_without_the_key_still_runs`.
  - `test_the_predict_form_checkbox_sets_the_payload` (web).
- [ ] **Step 2:** `uv run pytest tests/unit/test_batch_predict.py tests/unit/test_handler_batch_predict.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** With contributions on, chunks are `CONTRIBUTION_CHUNK_ROWS` rows. The handler checks the cap again, because a payload can be old.
- [ ] **Step 4:** Run the tests above plus `tests/web/test_easyml.py -k predict`. Expected: PASS.
- [ ] **Step 5: Commit** "Batch prediction can add each row's contributions".
- [ ] **Review Focus:**
  - Column order and renames.
  - Cancellation still checks between chunks.
  - The default output is unchanged.

### Task 10: Fione Serving opt-in contributions — careful review

**Files:**
- Modify:
  - `src/fione_serving/app.py`: `_instances` `:216`, `Predictor._predict_frame` `:180`, `create_app`;
  - `docs/serving.md`;
  - `docs/configuration.md` ("Fione Serving" table);
  - `docs/known-limitations.md`: the serving line.
- Test: `tests/contract/test_serving_contract.py`.

**Interfaces:**
- Consumes: `contributions`, `Contributions.slots` (Task 1).
- Produces:
  - `DEFAULT_MAX_CONTRIBUTION_INSTANCES = 1_000` (`FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES`);
  - `DEFAULT_MAX_CONTRIBUTION_REQUESTS = 2` (`FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS`), the number of contribution requests in flight;
  - `_request(body, max_instances, max_contribution_instances) -> tuple[list, bool]`;
  - `Predictor.predict(instances, *, contributions: bool = False)`;
  - a successful row with contributions has its usual keys, then `"contributions": {"bias": float, "columns": {column: float}}`, with the columns in `model.columns` order:
    - binary explains `class_probabilities[1]`;
    - multiclass explains `class_probabilities[index]`;
    - regression explains `value`;
  - a failing row stays `{"exception": msg}`;
  - `/model` does not change.

- [ ] **Step 1: Write the failing contract tests:**
  - `test_default_bytes_are_unchanged`: the body with `"contributions": false` gives exactly the same response text as the body without the key, for iris and for regression.
  - `test_contributions_key_order`: `list(row) == ["label","index","class_probabilities","contributions"]`.
  - `test_contributions_are_additive[binary|multiclass|regression]` (1e-6 after JSON).
  - `test_non_bool_contributions_is_400` (`"yes"`, `1`, `null`).
  - `test_too_many_contribution_instances_is_413`.
  - `test_failing_row_has_no_contributions`.
  - `test_in_flight_cap_returns_503`: hold the semaphore. Expected: 503 with `Retry-After: 1`, and a plain request still gives 200.
  - `test_model_description_is_unchanged`: the `/model` keys equal the Phase 1 list.
  - `test_a_column_named_BiasTerm_or_bias_stays_in_columns`.
- [ ] **Step 2:** `uv run pytest tests/contract -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Contributions are computed inside the same locked `_predict_frame` call as the prediction, so the bisect fallback covers them too.
  - The in-flight semaphore is acquired without blocking, before the threadpool, and released in `finally`.
  - Docs:
    - `serving.md`: the request and response, what is explained, and that the values are approximate and in probability space;
    - `configuration.md`: two rows;
    - known-limitations: keep "no rate or concurrency limit" for predictions and mention the contributions cap.
    - Both pages also say that plain predictions wait while a contribution request holds the model lock.
- [ ] **Step 4:** `uv run pytest tests/contract tests/unit/test_docs.py -q`. Expected: PASS.
- [ ] **Step 5: Commit** "Fione Serving: opt-in per-row contributions with their own limits".
- [ ] **Review Focus:**
  - Byte identity of the default path.
  - The semaphore is released when the body is rejected.
  - Floats go through `jsonable`.
  - The contribution cap is checked before any work.

### Task 11: Model page — diagnostics in the Metrics tab

**Files:**
- Modify:
  - `src/fione/web/models_ui.py`: `model_page` `:349`;
  - `templates/model.html`, which has the `model.not_stored` / `model.metrics_missing` notes;
  - `static/js/charts.js`, `static/css/app.css`;
  - i18n;
  - `scripts/ui-screenshots.py`.
- Test: `tests/web/test_models_ui.py`, `tests/web/test_contrast.py`.

**Interfaces:**
- Consumes: `ModelRecord.diagnostics` (Task 3).
- Produces:
  - `charts.js`:
    - `scan(root)`, run at start-up and on `htmx:load`; it skips elements already drawn (`data-chart-ready`);
    - a new spec type `lines`: `{type: "lines", series: [{name, points: [[x, y]], faint?: bool}], x_type: "value" | "category", categories?, labels, values, label, x_name, y_name, x_min?, x_max?, y_min?, y_max?}`. Faint series are thin, muted, left out of the legend and silent in tooltips.
    - `scatter`'s `line` gains an optional `step`, default `"end"`, used here for the y = x diagonal.
  - Every chart spec carries `labels` and `values` of equal length, because the macro's text alternative needs them.
  - `models_ui._diagnostics_view(record, lang) -> dict | None`, with:
    - `confusion: {labels, rows: [[{count, share, level 0..5}]]}`;
    - `per_class`;
    - `roc_chart`, `pr_chart`, `calibration_chart`;
    - `residual_chart` (bar), `scatter_chart`.

    A malformed or missing part is left out, and the page never fails because of it.
  - CSS classes `cm-0`..`cm-5`, with row shares bucketed at 0, ≤.1, ≤.25, ≤.5, ≤.75 and >.75. Light and dark tokens meet WCAG AA against the cell text.
  - i18n `model.diagnostics_missing` replaces `model.metrics_missing` (removed from en and ja), plus `model.diag.*`.

- [ ] **Step 1: Write the failing tests:**
  - `test_binary_diagnostics_render`: a 2×2 table with the counts, and ROC/PR/calibration chart blocks that parse as JSON.
  - `test_multiclass_has_no_roc_and_shows_other_beyond_30`.
  - `test_regression_shows_residuals_and_scatter`.
  - `test_phase1_model_shows_the_missing_note` (200).
  - `test_malformed_diagnostics_do_not_break_the_page`: `{"task": "classification", "confusion": "x"}` gives 200.
  - `test_hostile_label_is_escaped`: `<script>` is absent from the HTML, and `<` is in the JSON.
  - `test_every_chart_spec_has_matching_labels_and_values`: a helper over all `application/json` blocks.
  - `test_no_inline_style_attributes`.
  - `test_contrast.py` covers the `cm-*` pairs.
- [ ] **Step 2:** `uv run pytest tests/web/test_models_ui.py tests/web/test_contrast.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The confusion matrix is an HTML table with `scope` headers and class labels in `cell-name`.
- [ ] **Step 4:** Run the tests above plus `tests/unit/test_i18n.py`. Expected: PASS. Then `uv run python scripts/ui-screenshots.py <out-dir>`, with shots of the metrics tab added. Expected: exit 0, with no console or CSP errors. Review the light and dark PNGs at desktop and phone width.
- [ ] **Step 5: Commit** "Model page: confusion matrix, ROC/PR, calibration and residual charts".
- [ ] **Review Focus:**
  - Strict CSP: no inline styles.
  - Phone width has no sideways scroll.
  - Charts in hidden tabs still size.
  - Text alternatives.

### Task 12: Explain tab, PD fragment, recompute, and the per-row "why"

**Files:**
- Modify:
  - `src/fione/web/models_ui.py`;
  - `src/fione/web/easyml.py`: `prediction_result` `:765`, and the summary's top inputs;
  - templates `model.html`, `result.html`, `summary.html`, new `_pd.html` and `_why.html`;
  - i18n;
  - `tests/web/test_routes.py` (`MODEL_ROUTES`, `MODEL_PATHS`, the EasyML table);
  - `scripts/ui-screenshots.py`.
- Test: `tests/web/test_models_ui.py`, `tests/web/test_easyml.py`.

**Interfaces:**
- Consumes: Tasks 4, 7, 8 (`LiveModels`, `get_explanation`, `latest_explain_job`, `submit_explain`, `read_dataset_spread`, `read_dataset_rows`).
- Produces the routes below. `READ` and `WRITE_POST` are the tuples in `test_routes.py`.

  | Route | Access | What it does |
  |---|---|---|
  | Route | Table in `test_routes.py` | Codes | What it does |
  |---|---|---|---|
  | `GET /projects/{pid}/models/{mid}/explain/pd?column=&class=` | `MODEL_ROUTES` / `MODEL_PATHS` | `READ` | Fragment `_pd.html` |
  | `POST /projects/{pid}/models/{mid}/explain` | `MODEL_ROUTES` / `MODEL_PATHS` | `WRITE_POST` | `action()` (CSRF and Origin); optional form `dataset_id`; then `submit_explain` and 303 to `?tab=explain` |
  | `GET /projects/{pid}/jobs/{jid}/result/why` | `EASYML_ROUTES` / `ROUTE_PATHS` | `(303, 200, 200, 200, 404)`, as `/result` | Fragment `_why.html` |

  The Explain tab is `?tab=explain` on the existing model page (after "importance"), so it needs no new route row.

  - **The Explain tab:**
    - importance as an `hbar` chart of shares in %;
    - the precomputed PD columns, the first one drawn as `lines` (the PD line plus faint ICE lines);
    - a GET column picker using `hx-get` to the fragment;
    - by status: none, queued or running (with a job link), failed (redacted message), done;
    - for writers, a recompute form with a dataset select: the project's datasets that hold every model column, the model's own first.
  - **The PD fragment** uses the precomputed curve when one exists, without loading the model. Otherwise it computes through `LiveModels` on `read_dataset_spread(PD_ROWS)` of the model's dataset. `Busy` returns status 200 with `explain.busy`, so that HTMX swaps it in. `Untrusted` gives `explain.untrusted`, the same way. A missing dataset gives `explain.no_dataset`.
  - **The "why" fragment** shows the first `WHY_ROWS = 5` rows of the job's source dataset (`job.payload["dataset_id"]`) through `read_dataset_rows(0, 5)`. That source keeps the input order, and the prediction output may lack inputs because of `include_columns`.
    - Each row shows its prediction, the top 5 contributions by |value|, "other columns" as a sum, and the average prediction.
    - Units: percentage points for classification, target units for regression.
    - Magnitude is a `<meter>`, and the sign is text plus a `contrib-up` / `contrib-down` class.
    - A missing model or dataset, or `Busy`, gives a message.
  - **`result.html`** loads the fragment with `hx-trigger="load"`.
  - **The EasyML summary's top inputs** use the contribution shares once an explanation is done, and gain importance otherwise (`summary.top_inputs_hint_contrib`).

- [ ] **Step 1: Write the failing tests:**
  - `test_explain_tab_states[none|queued|done|failed]`, for a writer and for a viewer. The viewer gets no recompute form.
  - `test_precomputed_pd_does_not_load_the_model`: a `LiveModels.use` spy is not called.
  - `test_other_column_pd_is_computed`.
  - `test_pd_busy_message`.
  - `test_why_rows_add_up`: per row, the shown contributions plus "other" plus the average prediction equal the shown prediction, to the displayed rounding.
  - `test_why_with_deleted_source_dataset`.
  - `test_hostile_column_names_are_escaped`.
  - `test_recompute_needs_csrf_and_same_origin` (403s).
  - `test_imported_model_recompute_offers_a_dataset_choice`.
  - The `test_routes.py` rows for the three routes × personas.
  - `test_untrusted_model_is_not_loaded_in_the_web_process`: for a `trusted=0` model, the PD fragment on a column with no precomputed curve and the "why" fragment show `explain.untrusted`, and the `LiveModels.use` spy is not called.
- [ ] **Step 2:** `uv run pytest tests/web -q -k "explain or why or routes"`. Expected: FAIL.
- [ ] **Step 3: Implement.** Make the screenshot script poll `GET /api/v1/models/{id}/explanations` until it reports `done` before shooting the Explain tab, and wait for the "why" swap before shooting the result page.
- [ ] **Step 4:** `uv run pytest tests/web tests/unit/test_i18n.py -q`. Expected: PASS. Then `uv run python scripts/ui-screenshots.py <out-dir>`. Expected: exit 0. Review the Explain tab, the PD fragment and the result page in en and ja, light and dark, desktop and phone.
- [ ] **Step 5: Commit** "Model page explanations, partial dependence picker and per-row reasons on the prediction result".
- [ ] **Review Focus:**
  - GET fragments are side-effect free.
  - Viewers can read but not recompute.
  - The fragments are re-scanned for charts.
  - Wording for ML newcomers (EasyML).

### Task 13: Tools, documentation, acceptance and e2e

**Files:**
- Modify:
  - `src/fione/tools/builtin.py`: `_get_feature_importance` `:268`, registration `:485`, the privacy docstring;
  - `README.md`, `README.ja.md` (feature list);
  - `docs/known-limitations.md` (en and the Japanese summary);
  - `tests/e2e/test_easyml_flow.py`, `tests/e2e/test_serving_flow.py`.
- Create: `tests/acceptance/test_explain_adult.py`.
- Test: `tests/unit/test_tools.py`.

**Interfaces:**
- Consumes: Tasks 3, 7, 10.
- Produces these tools, with flat schemas and `read_only=True`:
  - `get_model_diagnostics(model_id)`. Numbers are kept.
    - Without `allow_samples`: no `labels` (only `n_classes`), no regression `points`, and `labels_hidden` / `points_hidden: true`.
    - With `allow_samples`: up to 50 labels, each cleaned to ≤ 50 characters.
  - `get_partial_dependence(model_id, column)`. Precomputed only, and never computes. Not available gives `{"available": false, "status"}`.
    - The PD `average` is returned without the ICE lines.
    - Categorical `grid` values are hidden without `allow_samples` (`grid_hidden: true`, grid indices returned).
  - `get_feature_importance(model_id, source: "gain" | "contributions" = "gain")`. Contributions that are not computed give `ToolError("contribution importance is not computed yet; run the explain job")`.

- [ ] **Step 1: Write the failing tool tests:**
  - `test_sentinel_never_leaks_from_new_tools`: class label, categorical level and regression target value are all set to `SECRET-CELL-VALUE`, with `allow_samples=False`.
  - `test_allow_samples_shows_truncated_labels`.
  - `test_importance_source_contributions`.
  - `test_pd_not_available`.
  - `test_new_tools_are_flat_and_read_only`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_tools.py -q`. Expected: FAIL. Implement, then run again. Expected: PASS. Commit "Assistant tools: diagnostics, partial dependence, importance from contributions".
- [ ] **Step 3: Acceptance** (`@pytest.mark.acceptance`, Adult on OpenML v2, 120 s, idle machine):
  - additivity on 1,000 test rows ≤ 1e-5;
  - contributions for 100 rows through `LiveModels` ≤ 2 s;
  - `len(json.dumps(model.diagnostics)) ≤ 64 KiB`;
  - explain payload ≤ 1 MiB and explain job ≤ 60 s;
  - PD for one column ≤ 5 s.

  Run `uv run pytest -m acceptance tests/acceptance/test_explain_adult.py -q`. Expected: PASS. Record the timings in the commit message body.
- [ ] **Step 4: e2e** (needs Docker):
  - the EasyML flow waits for the Explain tab's importance chart and for the result page's "why" rows;
  - the serving flow posts `"contributions": true` and checks additivity.

  Run `uv run pytest -m e2e tests/e2e -q`. Expected: PASS, or recorded as not run where Docker is unavailable.
- [ ] **Step 5: Docs:**
  - README (en/ja): explanations, diagnostics and leak warnings.
  - known-limitations (en, and the Japanese summary):
    - contributions are additive approximations in probability space, and ExtraTrees uses Saabas;
    - explanations come from the training dataset, so imported models need one chosen;
    - the web process now loads trusted models for small explanation requests, viewers' included, and keeps up to 2 models / 512 MiB loaded; models imported without a valid signature are explained only by the explain job;
    - leak scores are warnings and can be wrong both ways;
    - diagnostics come from the OOF predictions and are slightly optimistic;
    - exports that carry diagnostics are refused by installs without this feature.

  Run `uv run pytest tests/unit/test_docs.py -q`. Expected: PASS. Then `uv run pytest -q && uv run ruff check . && uv run python scripts/check_licenses.py`. Expected: PASS. Commit "Document model explanations and their limits; Adult acceptance checks".
- [ ] **Review Focus:**
  - Privacy gating on every new tool field.
  - The docs match the behaviour: approximate, warn-only, the caps.
  - No `FIONE_*` name is left undocumented.

---

## Self-Review Notes

- **Spec coverage:**
  - Spec 6, "model explanations" (variable importance, CV metrics, confusion matrix / residuals, SHAP and partial dependence deferred to this phase): Tasks 1-4 and 11-12.
  - Spec 6, "target leak suspects": Tasks 5-6.
  - Spec 8, `contributions` in Phase 2: Task 10.
  - Spec 9, typed read-only tools and data handling: Tasks 6 and 13.
  - Spec 5.7, budget: diagnostics run in the reserve (Task 2).
  - Spec 10.5, unit / API / contract / e2e / acceptance tests: every task, plus Task 13.
  - Notebook integration (`fione-sdk`, Jupyter) is Phase 2b and not in this plan.
- **Consistency:** the names other tasks rely on are fixed in Interfaces:
  - `Contributions.slots`;
  - `contribution_columns`;
  - `LiveModels.use` / `Busy`;
  - `read_dataset_spread`;
  - `SCORE_REASONS`;
  - `model_columns`;
  - `explain_after_training`.

  Everywhere: binary explains `classes_[1]`, multiclass the predicted class, and the bias sits outside the column map.
- **Risks:**
  - The multiclass path integral is an approximation with an exact-sum fold-in.
  - Leak-score thresholds come from a small benchmark, so the scores are warn-only.
  - The Task 0 outcome may add an engine fix outside this plan.
