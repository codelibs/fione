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

## Notes

- Frames travel as CSV, so dtypes do not round-trip exactly: `read` infers them again
  (dates come back as text, for example).
- A response that is not a 2xx raises `fione_sdk.FioneError` with the HTTP `status`, the
  API's error `code` and a `message`. A redirect is an error too (it usually means
  `FIONE_URL` should be the `https` address); the client never follows redirects.
- Transport errors (`httpx.ConnectError`, timeouts) are not wrapped and propagate as they
  are.
