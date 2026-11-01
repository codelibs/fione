"""Paired holdout benchmark of the AutoML engine on small OpenML datasets.

Why: one dataset says little (differences of a few thousandths are noise at these sizes), so an
engine change is judged on many datasets and many splits, each pair of runs on the same split.

    uv run python scripts/benchmark_automl.py run --label base --out base.csv --jobs 3
    uv run python scripts/benchmark_automl.py run --label new --out new.csv --jobs 3 \\
        --config '{"feature_engineering": false}'
    uv run python scripts/benchmark_automl.py compare base.csv new.csv

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
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
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
    "members",
]


def load(name: str, data_home: str) -> tuple[pd.DataFrame, str, str]:
    """(frame with the target column, target name, task)."""
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


def run_one(job: tuple[str, int, str, dict, str, dict]) -> dict:
    """Fit one dataset on one split; the holdout numbers are the row."""
    from fione.engine.automl import AutoML
    from fione.engine.config import TrainConfig

    name, split, label, config, data_home, patches = job
    for target_name, value in patches.items():  # "package.module.NAME": JSON value
        module, attribute = target_name.rsplit(".", 1)
        setattr(importlib.import_module(module), attribute, value)
    frame, target, task = load(name, data_home)
    strat = frame[target] if task == "classification" else None
    train, test = train_test_split(frame, test_size=0.2, random_state=split, stratify=strat)
    started = time.monotonic()
    model = AutoML(TrainConfig(target=target, task=task, **config)).fit(train)
    secs = time.monotonic() - started
    y = test[target].to_numpy()
    row = dict(label=label, dataset=name, split=split, task=task, secs=round(secs, 1))
    row.update(trials=len(model.trials), stop=model.stop_reason, accuracy=np.nan, auc=np.nan)
    if task == "classification":
        proba = model.predict_proba(test)
        classes = list(proba.columns)
        row["loss"] = log_loss(y, proba.to_numpy(), labels=classes)
        row["accuracy"] = accuracy_score(y, proba.idxmax(axis=1).to_numpy())
        if len(classes) == 2:
            row["auc"] = roc_auc_score(y == classes[1], proba[classes[1]].to_numpy())
        row["cv_loss"] = model.metrics.get("logloss", np.nan)
    else:
        row["loss"] = float(np.sqrt(np.mean((y - model.predict(test).to_numpy()) ** 2)))
        row["cv_loss"] = model.metrics.get("rmse", np.nan)
    row["members"] = ",".join(f"{m.spec.name}:{m.weight:.2f}" for m in model.members)
    return row


def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    done = set()
    if out.exists():
        old = pd.read_csv(out)
        done = set(zip(old["dataset"], old["split"], old["label"], strict=True))
    names = args.datasets.split(",") if args.datasets else list(DATASETS)
    config = json.loads(args.config)
    patches = {}
    for item in args.patch:
        key, value = item.split("=", 1)
        patches[key] = json.loads(value)
    jobs = [
        (name, split, args.label, config, args.data_home, patches)
        for split in range(args.splits)
        for name in names
        if (name, split, args.label) not in done
    ]
    for name in names:  # download once, before the workers need it
        load(name, args.data_home)
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
    p.add_argument("--data-home", default=str(Path.home() / ".cache" / "fione-openml"))
    p.set_defaults(func=run)
    c = sub.add_parser("compare", help="paired comparison of two result files")
    c.add_argument("base")
    c.add_argument("new")
    c.set_defaults(func=compare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
