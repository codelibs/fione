"""Paired holdout benchmark of the AutoML engine on small OpenML datasets and local CSV files.

Why: one dataset says little (differences of a few thousandths are noise at these sizes), so an
engine change is judged on many datasets and many splits, each pair of runs on the same split.

    uv run python scripts/benchmark_automl.py run --label base --out base.csv --jobs 3
    uv run python scripts/benchmark_automl.py run --label new --out new.csv --jobs 3 \\
        --config '{"feature_engineering": false}'
    uv run python scripts/benchmark_automl.py compare base.csv new.csv

Your own CSV files join with ``--local-spec spec.json`` (then only they run, unless
``--datasets`` names others). The spec maps a name to its file (relative to the spec), the target,
the task and the metric that scores the fit, and may drop columns such as an ID:

    {"mydata": {"file": "mydata/train.csv", "target": "y", "task": "classification",
                "metric": "auc", "drop": ["id"]}}

The metric is one of ``accuracy``, ``balanced_accuracy``, ``auc``, ``average_precision`` and ``f1``
(the last three for two classes; ``f1`` is of the second class), ``rmse``, ``mae`` and ``rmsle``;
it goes to the ``metric`` and ``score`` columns beside the log loss / RMSE of ``loss``.
With ``"order": "column"`` the holdout is the last 20% of the rows in the order of that column
(rows of the same value stay together) instead of a random one, for data whose test period comes
after the training period; every split is then the same holdout, and only the seed of the fit
differs. The column stays a feature unless ``drop`` names it; name it in ``--config`` as
``{"time_column": "column"}`` to also validate in order of it (add it to ``ignored_columns`` to
leave it out of the features).
Keep the spec, the data and the results out of the repository.

``run`` fits every dataset on ``--splits`` random 80/20 splits (the split number is the seed) and
appends one row per fit to ``--out``; rows already there are skipped, so an interrupted run
resumes. Datasets are downloaded from OpenML once (``--data-home``). ``compare`` prints, per
dataset, the mean relative change of the holdout loss (log loss, or RMSE for regression; below 0
is better) with its standard error over the splits, then the average over datasets.
"""

import argparse
import importlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import fetch_openml
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# name -> (task, columns to drop). The target is OpenML's default target.
DATASETS: dict[str, tuple[str, list[str]]] = {
    "credit-g": ("classification", []),
    "diabetes": ("classification", []),
    "blood-transfusion-service-center": ("classification", []),
    "ilpd": ("classification", []),
    "kc1": ("classification", []),
    "qsar-biodeg": ("classification", []),
    "phoneme": ("classification", []),
    "vehicle": ("classification", []),
    "segment": ("classification", []),
    "titanic": ("classification", ["boat", "body", "home.dest"]),  # the last three leak the answer
    "house_prices": ("regression", []),
    "Moneyball": ("regression", []),
    "boston": ("regression", []),
    "cholesterol": ("regression", []),
    "kin8nm": ("regression", []),
}
VERSIONS = {"titanic": 1}  # the default (newest) version has other columns
COLUMNS = [
    "label",
    "dataset",
    "split",
    "task",
    "secs",
    "trials",
    "stop",
    "cv_loss",
    "loss",
    "accuracy",
    "auc",
    "metric",
    "score",
    "members",
]
METRICS = {
    "accuracy",
    "balanced_accuracy",
    "auc",
    "average_precision",
    "f1",
    "rmse",
    "mae",
    "rmsle",
}


def load_spec(path: str | None) -> dict[str, dict]:
    """The local datasets of a spec file, with ``file`` made absolute."""
    if not path:
        return {}
    spec_path = Path(path).resolve()
    spec = json.loads(spec_path.read_text())
    for name, entry in spec.items():
        if entry.get("task") not in ("classification", "regression"):
            raise SystemExit(f"{name}: task must be classification or regression")
        if entry.get("metric") not in METRICS:
            raise SystemExit(f"{name}: metric must be one of {sorted(METRICS)}")
        if not entry.get("target") or not entry.get("file"):
            raise SystemExit(f"{name}: target and file are required")
        entry["file"] = str(spec_path.parent / entry["file"])
    return spec


def load(name: str, data_home: str, local: dict[str, dict]) -> tuple[pd.DataFrame, str, str]:
    """(frame with the target column, target name, task)."""
    if name in local:
        entry = local[name]
        kept = [
            c for c in entry.get("drop", []) if c != entry.get("order")
        ]  # dropped after the split
        frame = pd.read_csv(entry["file"]).drop(columns=kept)
        target, task = entry["target"], entry["task"]
        frame[target] = frame[target].astype(str if task == "classification" else float)
        return frame, target, task
    task, drop = DATASETS[name]
    bunch = fetch_openml(
        name=name,
        version=VERSIONS.get(name, "active"),
        as_frame=True,
        parser="liac-arff",
        data_home=data_home,
    )
    frame = bunch.frame.drop(columns=drop)
    target = bunch.target_names[0]
    if task == "classification":
        frame[target] = frame[target].astype(str)
    else:
        frame[target] = frame[target].astype(float)
    return frame, target, task


def score(
    metric: str, y: np.ndarray, pred: pd.DataFrame | np.ndarray, labels: np.ndarray | None = None
) -> float:
    """The dataset's own metric; ``pred`` is the class probabilities or the regression values,
    and ``labels`` the model's predicted classes (default: the most probable)."""
    if metric == "rmse":
        return float(np.sqrt(np.mean((y - pred) ** 2)))
    if metric == "mae":
        return float(np.mean(np.abs(y - pred)))
    if metric == "rmsle":
        return float(np.sqrt(np.mean((np.log1p(np.clip(pred, 0, None)) - np.log1p(y)) ** 2)))
    classes = list(pred.columns)
    if metric == "auc":
        if len(classes) != 2:
            raise SystemExit("auc needs exactly two classes")
        return float(roc_auc_score(y == classes[1], pred[classes[1]].to_numpy()))
    if metric == "average_precision":
        if len(classes) != 2:
            raise SystemExit("average_precision needs exactly two classes")
        return float(average_precision_score(y == classes[1], pred[classes[1]].to_numpy()))
    labels = pred.idxmax(axis=1).to_numpy() if labels is None else labels
    if metric == "balanced_accuracy":
        return float(balanced_accuracy_score(y, labels))
    if metric == "f1":
        if len(classes) != 2:
            raise SystemExit("f1 needs exactly two classes")
        return float(f1_score(y == classes[1], labels == classes[1]))
    if metric != "accuracy":
        raise SystemExit(f"unknown metric {metric}")
    return float(accuracy_score(y, labels))


def last_fifth(frame: pd.DataFrame, order: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The first 80% of the rows in the order of ``order``, and the last 20%; rows of one value
    are on the same side (the cut moves to the start of its value)."""
    if order not in frame.columns:
        raise SystemExit(f"order column {order!r} is not in the data")
    ranked = frame.sort_values(order, kind="stable")
    values = ranked[order].to_numpy()
    cut = int(np.searchsorted(values, values[int(len(values) * 0.8)], side="left"))
    if cut == 0:
        raise SystemExit(f"order column {order!r} has too few different values")
    return ranked.iloc[:cut], ranked.iloc[cut:]


def run_one(job: tuple[str, int, str, dict, str, dict, dict]) -> dict:
    """Fit one dataset on one split; the holdout numbers are the row."""
    from fione.engine.automl import AutoML
    from fione.engine.config import TrainConfig

    name, split, label, config, data_home, patches, local = job
    for target_name, value in patches.items():  # "package.module.NAME": JSON value
        module, attribute = target_name.rsplit(".", 1)
        setattr(importlib.import_module(module), attribute, value)
    frame, target, task = load(name, data_home, local)
    entry = local.get(name, {})
    if entry.get("order"):
        train, test = last_fifth(frame, entry["order"])
        if entry["order"] in entry.get("drop", []) and config.get("time_column") != entry["order"]:
            train, test = train.drop(columns=entry["order"]), test.drop(columns=entry["order"])
    else:
        strat = frame[target] if task == "classification" else None
        train, test = train_test_split(frame, test_size=0.2, random_state=split, stratify=strat)
    started = time.monotonic()
    model = AutoML(TrainConfig(**{"target": target, "task": task, **config})).fit(train)
    secs = time.monotonic() - started
    y = test[target].to_numpy()
    row = dict(label=label, dataset=name, split=split, task=task, secs=round(secs, 1))
    row.update(trials=len(model.trials), stop=model.stop_reason, accuracy=np.nan, auc=np.nan)
    metric = local.get(name, {}).get("metric")
    row["metric"] = metric
    if task == "classification":
        proba = model.predict_proba(test)
        classes = list(proba.columns)
        labels = model.predict(test).to_numpy()  # follows the model's decision rule
        if metric:
            row["score"] = score(metric, y, proba, labels)
        row["loss"] = log_loss(y, proba.to_numpy(), labels=classes)
        row["accuracy"] = accuracy_score(y, labels)
        if len(classes) == 2:
            row["auc"] = roc_auc_score(y == classes[1], proba[classes[1]].to_numpy())
        row["cv_loss"] = model.metrics.get("logloss", np.nan)
    else:
        predicted = model.predict(test).to_numpy()
        if metric:
            row["score"] = score(metric, y, predicted)
        row["loss"] = float(np.sqrt(np.mean((y - predicted) ** 2)))
        row["cv_loss"] = model.metrics.get("rmse", np.nan)
    row["members"] = ",".join(f"{m.key}:{m.weight:.2f}" for m in model.members)
    return row


def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    local = load_spec(args.local_spec)
    done = set()
    if out.exists():
        old = pd.read_csv(out)
        if list(old.columns) != COLUMNS:
            raise SystemExit(f"{out} has other columns than this version writes; use a new --out")
        done = set(zip(old["dataset"], old["split"], old["label"], strict=True))
    names = args.datasets.split(",") if args.datasets else list(local or DATASETS)
    config = json.loads(args.config)
    patches = {}
    for item in args.patch:
        key, value = item.split("=", 1)
        patches[key] = json.loads(value)
    jobs = [
        (name, split, args.label, config, args.data_home, patches, local)
        for split in range(args.splits)
        for name in names
        if (name, split, args.label) not in done
    ]
    for name in names:  # download once, before the workers need it
        load(name, args.data_home, local)
    print(f"{len(jobs)} fits", flush=True)
    write_header = not out.exists()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_one, job): job for job in jobs}
        for future in as_completed(futures):
            name, split = futures[future][:2]
            try:
                row = future.result()
            except Exception as e:  # one failing fit must not lose the others
                print(f"{name} split {split}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                continue
            pd.DataFrame([row], columns=COLUMNS).to_csv(
                out, mode="a", header=write_header, index=False
            )
            write_header = False
            print(f"{name} split {split}: loss {row['loss']:.4f} in {row['secs']}s", flush=True)


def compare(args: argparse.Namespace) -> None:
    a, b = pd.read_csv(args.base), pd.read_csv(args.new)
    for name, frame in (("base", a), ("new", b)):
        if frame["label"].nunique() > 1:
            raise SystemExit(
                f"the {name} file holds several arms: {sorted(frame['label'].unique())}"
            )
    if args.metric == "error":  # 1 - accuracy, for the classification datasets
        a, b = a.dropna(subset=["accuracy"]).copy(), b.dropna(subset=["accuracy"]).copy()
        a["loss"], b["loss"] = 1 - a["accuracy"], 1 - b["accuracy"]
        a = a[a["loss"] > 0]  # a change relative to no errors at all is undefined
    pairs = a.merge(b, on=["dataset", "split"], suffixes=("_a", "_b"))
    pairs["change"] = (pairs["loss_b"] - pairs["loss_a"]) / pairs["loss_a"]
    pairs["time"] = pairs["secs_b"] / pairs["secs_a"]
    rows = []
    for name, group in pairs.groupby("dataset", sort=False):
        n = len(group)
        error = group["change"].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        rows.append(
            dict(
                dataset=name,
                splits=n,
                change=group["change"].mean(),
                se=error,
                wins=int((group["change"] < 0).sum()),
                time=group["secs_b"].mean() / group["secs_a"].mean(),
            )
        )
    table = pd.DataFrame(rows)
    shown = table.assign(change=(table["change"] * 100).round(2), se=(table["se"] * 100).round(2))
    print(
        shown.rename(columns={"change": "change %", "se": "se %", "time": "time x"})
        .round(2)
        .to_string(index=False)
    )
    mean = table["change"].mean() * 100
    error = table["change"].std(ddof=1) / np.sqrt(len(table)) * 100 if len(table) > 1 else np.nan
    better, worse = int((table["change"] < 0).sum()), int((table["change"] > 0).sum())
    print(
        f"\nmean change over {len(table)} datasets: {mean:+.2f} % (se {error:.2f} %); "
        f"better on {better}, worse on {worse}; time x{table['time'].mean():.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("run", help="fit the datasets and append the holdout results")
    p.add_argument("--label", required=True, help="name of this arm in the results")
    p.add_argument("--out", required=True)
    p.add_argument("--splits", type=int, default=3)
    p.add_argument("--jobs", type=int, default=2, help="fits in parallel")
    p.add_argument("--datasets", help="comma-separated subset (default: all)")
    p.add_argument("--config", default="{}", help="TrainConfig fields as JSON")
    p.add_argument(
        "--patch",
        action="append",
        default=[],
        help="set a module constant for this arm, e.g. fione.engine.automl.BAG_EXTRA=0",
    )
    p.add_argument("--local-spec", help="JSON file describing local CSV datasets (see above)")
    p.add_argument("--data-home", default=str(Path.home() / ".cache" / "fione-openml"))
    p.set_defaults(func=run)
    c = sub.add_parser("compare", help="paired comparison of two result files")
    c.add_argument("base")
    c.add_argument("new")
    c.add_argument(
        "--metric",
        choices=["loss", "error"],
        default="loss",
        help="loss: log loss or RMSE (default); error: 1 - accuracy of the classification fits",
    )
    c.set_defaults(func=compare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
