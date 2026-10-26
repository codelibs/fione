# fione-sdk

Python client for Fione, the AutoML server. It talks to the Fione API with an API token, so
you can use it from a notebook or a script. It needs Python 3.12 or later.

## Install

```sh
pip install ./sdk
```

## Configure

`Client()` reads two environment variables; `Client(url=..., token=...)` takes them as
arguments instead.

| Variable | What it is |
|---|---|
| `FIONE_URL` | The address of your Fione server, for example `http://localhost:8080`. |
| `FIONE_TOKEN` | An API token (create one on the Account page). |

Other options:

- `timeout=` is the request timeout in seconds (default 60).
- `http=` is an `httpx.Client` to send through instead of the client's own. `url` and
  `timeout` are then ignored, and the token goes to wherever that client points.

## Example

```python
import pandas as pd
from fione_sdk import Client

fione = Client()
project = fione.create_project("demo")
dataset = fione.upload(project["id"], pd.read_csv("train.csv"), "train")
print(fione.profile(project["id"], dataset["id"]))
frame = fione.read(project["id"], dataset["id"])
```

## Train, wait, predict

`train` queues AutoML training and returns a `Job`; `wait` blocks until it ends.

```python
job = fione.train(project["id"], dataset["id"], "species", max_runtime_secs=300)
for event in job.events(follow=True):  # progress, until the job has ended
    print(event["type"], event["data"])
job.wait()
model_id = job.result["model_id"]
print(fione.leaderboard(model_id))  # one row per model AutoML tried
print(fione.models(project["id"]))  # one row per model of the project

predictions = fione.predict(project["id"], model_id, new_rows)  # a "predict" column
```

- `train(project_id, dataset_id, target, *, name=None, **config)` takes the other training
  options as keyword arguments. The dataset must be a `train` dataset.
- `wait(timeout=None, poll=1.0, max_poll=10.0)` polls, doubling the interval up to
  `max_poll`. It raises `fione_sdk.JobFailed` (a `FioneError`) when the job failed or was
  cancelled: `code` is `"failed"` or `"cancelled"`, `message` the job's message, `job` the
  job and `status` 0 (no HTTP response is involved). It raises `TimeoutError` after `timeout` seconds and leaves the job running.
  Interrupting a wait (Ctrl-C in a notebook) cancels the job.
- `job.events(after=0, follow=False)` yields the job's events; with `follow=True` it waits
  for new ones until the job has ended. `job.refresh()` and `job.cancel()` update `job.data`;
  `job.status` and `job.result` read from it. `fione.job(job_id)` gets a job again later.
- `predict(project_id, model_id, df, *, include_columns=None, timeout=None)` uploads the
  frame as a temporary dataset, predicts on the server, reads the result back in the order
  of the rows and deletes the temporary dataset. It always deletes the upload, also when the
  prediction fails or times out. After `timeout` seconds (or on failure) it cancels its
  batch-predict job and raises `TimeoutError` (or `JobFailed`). The result dataset stays in
  the project; `include_columns` copies those input columns into it.

## Modules

`modules()` lists what the server can run. `run_module` queues one over a dataset and returns
a `Job`; the module runs on the server, not in your notebook, so it needs no packages here.

```python
job = fione.run_module(project["id"], "sort", dataset["id"], {"column": "age"})
job.wait()
sorted_frame = fione.read(project["id"], job.result["dataset_id"])
```

## Notes

- Frames travel as CSV, so dtypes do not round-trip exactly: `read` infers them again
  (dates come back as text, for example).
- A response that is not a 2xx raises `fione_sdk.FioneError` with the HTTP `status`, the
  API's error `code` and a `message`. A redirect is an error too (it usually means
  `FIONE_URL` should be the `https` address); the client never follows redirects.
- Transport errors (`httpx.ConnectError`, timeouts) are not wrapped and propagate as they
  are.
